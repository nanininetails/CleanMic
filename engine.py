import logging

import numpy as np
import noisereduce as nr

from base_engine import BaseAudioEngine

logger = logging.getLogger(__name__)


class AudioEngine(BaseAudioEngine):
    """STFT NoiseReduce engine."""

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
        self.calibration_complete = False

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
            outdata[:] = indata
            self._write_monitor(raw)
            if self.is_recording:
                self.record_buffer.append(raw.copy())      
            self._push_to_visual_queue(raw, raw)
            return

        raw_audio = indata[:, 0]

        # --- PHASE 1: CALIBRATION ---
        if self.is_calibrating:
            self.noise_buffer.extend(raw_audio)
            self.chunks_collected += 1
            target_chunks = int((self.sample_rate / self.chunk_size) * self.scan_time_seconds)

            if self.chunks_collected >= target_chunks:
                self.known_fan_noise = np.array(self.noise_buffer, dtype=np.float32)
                self.is_calibrating = False
                self.calibration_complete = True

            outdata[:] = indata
            self._write_monitor(raw_audio)
            if self.is_recording:
                self.record_buffer.append(raw_audio.copy())
            self._push_to_visual_queue(raw_audio, raw_audio)
            return

        # --- PHASE 2: ACTIVE SCRUBBING ---
        try:
            if self.known_fan_noise.size > 0:
                clean_audio = nr.reduce_noise(
                    y=raw_audio,
                    sr=self.sample_rate,
                    y_noise=self.known_fan_noise,
                    prop_decrease=self.scrub_power,
                    stationary=True,
                    n_std_thresh_stationary=self.hunting_focus,
                    time_mask_smooth_ms=int(self.word_fade_ms),
                    freq_mask_smooth_hz=int(self.voice_shield_hz),
                )
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

    # ------------------------------------------------------------------
    # Stream — adds calibration kick before base start_stream
    # ------------------------------------------------------------------

    def start_stream(self) -> None:
        self.start_calibration(self.scan_time_seconds)
        super().start_stream()