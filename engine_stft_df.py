from base_engine import BaseAudioEngine

import logging
import numpy as np
#import noisereduce as nr
import sys
import os
import scipy.signal as signal
import torch

import compat
compat.patch_torchaudio_backend()

from df.enhance import init_df, enhance

logger = logging.getLogger(__name__)

# PyTorch CPU optimisations — set once at module load
torch.set_num_threads(1)
torch.set_grad_enabled(False)


class AudioEngine(BaseAudioEngine):
    def __init__(self):
        super().__init__()
        self.chunk_size = 4096

        # Calibration
        self.scan_time_seconds = 4.0
        self.scrub_power = 0.98
        self.hunting_focus = 2.0
        self.word_fade_ms = 90
        self.voice_shield_hz = 400

        self.is_calibrating = False
        self.chunks_collected = 0
        self.noise_buffer: list = []
        self.known_fan_noise = np.array([], dtype=np.float32)
        self.noise_psd = None
        self.calibration_complete = False

        # STFT Perameters for Wiener filter
        self.n_fft = 2048
        self.hop_length = 512
        self.win_length = 2048
        self._window = np.hanning(self.n_fft)
        self._gain_smooth = None
        self._ola_buffer = np.zeros(self.n_fft, dtype=np.float32)
        self._ola_window_sum = np.zeros(self.n_fft, dtype=np.float32)

        # High-pass filter (removes sub-120 Hz rumble before neural processing)
        self.b, self.a = signal.butter(4, 120.0, "highpass", fs=self.sample_rate)
        self.zi = signal.lfilter_zi(self.b, self.a)  # per-block state; only touched in audio thread

        # Attenuation Limit
        self.atten_lim_db = 20

        logger.info("Booting DeepFilterNet AI... (Loading PyTorch Models)")
        if getattr(sys, 'frozen', False):
            model_base_dir = os.path.join(sys._MEIPASS, 'DeepFilterNet3')
        else:
            model_base_dir = None
        self.model, self.df_state, _ = init_df(model_base_dir=model_base_dir)
        logger.info("DeepFilterNet Ready.")

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def start_calibration(self, seconds: float) -> None:
        self.scan_time_seconds = float(seconds)
        self.noise_buffer = []
        self.chunks_collected = 0
        self.is_calibrating = True
        self.calibration_complete = False

    # ------------------------------------------------------------------
    # Audio callback
    # ------------------------------------------------------------------

    def _audio_callback(self, indata, outdata, frames, time, status):
        if status:
            logger.warning("Hardware warning: %s", status)
        if not self.is_running:
            outdata.fill(0)
            return

        # Guard: pass audio through unprocessed when not engaged
        if not self.is_engaged:
            raw = indata[:, 0].copy()
            gained_audio = np.clip(indata * self.output_gain, -1.0,1.0).astype(np.float32)
            outdata[:] = gained_audio

            gained_raw = gained_audio[:,0].copy()
            self._write_monitor(gained_raw)
            if self.is_recording:
                self.record_buffer.append(gained_raw)      
            self._push_to_visual_queue(raw, gained_raw)
            return

        raw_audio = indata[:, 0]

        # --- PHASE 1: CALIBRATION ---
        if self.is_calibrating:
            self.noise_buffer.extend(raw_audio)
            self.chunks_collected += 1
            target_chunks = int((self.sample_rate / self.chunk_size) * self.scan_time_seconds)

            if self.chunks_collected >= target_chunks:
                self.known_fan_noise = np.array(self.noise_buffer, dtype=np.float32)
                self.noise_psd = self._estimate_noise_psd(self.known_fan_noise)
                self._gain_smooth = None
                self.is_calibrating = False
                self.calibration_complete = True

            gained_audio = np.clip(indata * self.output_gain, -1.0, 1.0).astype(np.float32)
            outdata[:] = gained_audio

            gained_raw = gained_audio[:,0].copy()
            self._write_monitor(gained_raw)
            if self.is_recording:
                self.record_buffer.append(gained_raw)
            self._push_to_visual_queue(raw_audio, gained_raw)
            return

        # --- PHASE 2: ACTIVE SCRUBBING ---
        try:
            if self.noise_psd is not None:
                clean_audio = self._wiener_filter(raw_audio)

                # DeepFilter Stage
                filtered_audio, self.zi = signal.lfilter(self.b, self.a, clean_audio, zi=self.zi)
                filtered_audio = filtered_audio.astype(np.float32)
                audio_tensor = torch.from_numpy(filtered_audio).unsqueeze(0)
                clean_tensor = enhance(self.model, self.df_state, audio_tensor, atten_lim_db=self.atten_lim_db)
                clean_audio = clean_tensor.squeeze().numpy()

                clean_audio = self._apply_post_processing(clean_audio)
                clean_audio *= self.output_gain
                clean_audio = np.clip(clean_audio, -1.0, 1.0)
                outdata[:] = clean_audio.reshape(-1, 1).astype(np.float32)
                self._write_monitor(clean_audio)
                if self.is_recording:
                    self.record_buffer.append(clean_audio.copy())
                self._push_to_visual_queue(raw_audio, clean_audio)
            else:
                outdata[:] = indata
                self._write_monitor(raw_audio)
                if self.is_recording:
                    self.record_buffer.append(raw_audio.copy())
                self._push_to_visual_queue(raw_audio, raw_audio)
        except Exception as e:
            logger.warning("Audio processing error: %s", e)
            outdata[:] = indata
            self._write_monitor(raw_audio)
            if self.is_recording:
                self.record_buffer.append(raw_audio.copy())
            self._push_to_visual_queue(raw_audio, raw_audio)
    
    def _estimate_noise_psd(self, noise: np.ndarray) -> np.ndarray:
        n_frames = (len(noise) - self.n_fft) // self.hop_length
        psds = []
        for i in range(n_frames):
            frame = noise[i*self.hop_length:i*self.hop_length+self.n_fft]
            spec = np.fft.rfft(frame * self._window)
            psds.append(np.abs(spec)**2)
        return np.mean(psds, axis=0)

    def _wiener_filter(self, audio: np.ndarray) -> np.ndarray:
        n = len(audio)
        # Prepend carry-over from previous chunk
        padded = np.concatenate([self._ola_buffer[:self.n_fft], audio, np.zeros(self.n_fft, dtype=np.float32)])
        output = np.zeros(len(padded), dtype=np.float32)
        window_sum = np.zeros(len(padded), dtype=np.float32)

        for i in range(0, n + self.n_fft, self.hop_length):
            if i + self.n_fft > len(padded):
                break
            frame = padded[i:i+self.n_fft] * self._window
            spec = np.fft.rfft(frame)
            signal_psd = np.abs(spec)**2

            snr = np.maximum(signal_psd - self.noise_psd, 0) / (self.noise_psd + 1e-10)
            gain = np.maximum(snr / (snr + 1), 0.15)

            if self._gain_smooth is None:
                self._gain_smooth = gain
            else:
                self._gain_smooth = 0.97 * self._gain_smooth + 0.03 * gain

            frame_out = np.fft.irfft(spec * self._gain_smooth) * self._window
            output[i:i+self.n_fft] += frame_out
            window_sum[i:i+self.n_fft] += self._window**2

        window_sum = np.maximum(window_sum, 1e-8)
        result = output / window_sum

        # Save tail for next chunk
        self._ola_buffer = result[n:n+self.n_fft].copy()

        # Return only the current chunk's samples, offset by n_fft for the prepended carry-over
        return result[self.n_fft:self.n_fft+n].astype(np.float32)
    

    def start_stream(self) -> None:
        self._ola_buffer = np.zeros(self.n_fft, dtype=np.float32)
        self._ola_window_sum = np.zeros(self.n_fft, dtype=np.float32)
        self._gain_smooth = None
        self.zi = signal.lfilter_zi(self.b, self.a)
        self.start_calibration(self.scan_time_seconds)
        super().start_stream()