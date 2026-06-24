import logging
import sys
import os
import numpy as np
import scipy.signal as signal
import torch

import compat
compat.patch_torchaudio_backend()

from df.enhance import init_df, enhance
from base_engine import BaseAudioEngine

logger = logging.getLogger(__name__)

# PyTorch CPU optimisations — set once at module load
torch.set_num_threads(1)
torch.set_grad_enabled(False)


class AudioEngine(BaseAudioEngine):
    """DeepFilterNet neural engine."""

    def __init__(self):
        super().__init__()
        self.chunk_size = 4096

        # High-pass filter (removes sub-120 Hz rumble before neural processing)
        self.b, self.a = signal.butter(4, 120.0, "highpass", fs=self.sample_rate)
        self.zi = signal.lfilter_zi(self.b, self.a)  # per-block state; only touched in audio thread

        # Attenuation Limit
        self.atten_lim_db = None

        logger.info("Booting DeepFilterNet AI... (Loading PyTorch Models)")
        if getattr(sys, 'frozen', False):
            model_base_dir = os.path.join(sys._MEIPASS, 'DeepFilterNet3')
        else:
            model_base_dir = None
        self.model, self.df_state, _ = init_df(model_base_dir=model_base_dir)
        logger.info("DeepFilterNet Ready.")

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
            gained_audio = np.clip(indata * self.output_gain,-1.0,1.0).astype(np.float32)
            outdata[:] = gained_audio

            gained_raw = gained_audio[:,0].copy()
            self._write_monitor(gained_raw)
            if self.is_recording:
                self.record_buffer.append(gained_raw)
            self._push_to_visual_queue(raw, gained_raw)
            return

        raw_audio = indata[:, 0].copy()

        try:
            # 1. High-pass filter with continuous state (zi mutated only here — audio thread only)
            filtered_audio, self.zi = signal.lfilter(self.b, self.a, raw_audio, zi=self.zi)
            filtered_audio = filtered_audio.astype(np.float32)

            # 2. Neural inference
            audio_tensor = torch.from_numpy(filtered_audio).unsqueeze(0)
            clean_tensor = enhance(self.model, self.df_state, audio_tensor, atten_lim_db = self.atten_lim_db)
            clean_audio = clean_tensor.squeeze().numpy()
            clean_audio = self._apply_post_processing(clean_audio)
            clean_audio *= self.output_gain
            clean_audio = np.clip(clean_audio, -1.0, 1.0)

            outdata[:] = clean_audio.reshape(-1, 1).astype(np.float32)
            self._write_monitor(clean_audio)

            if self.is_recording:
                self.record_buffer.append(clean_audio.copy())

            self._push_to_visual_queue(raw_audio, clean_audio)

        except Exception as e:
            logger.warning("Processing error: %s", e)
            outdata[:] = indata
            self._write_monitor(raw_audio)
            if self.is_recording:
                self.record_buffer.append(raw_audio.copy())
            self._push_to_visual_queue(raw_audio, raw_audio)

    # ------------------------------------------------------------------
    # Stream — resets filter state on fresh boot
    # ------------------------------------------------------------------

    def start_stream(self) -> None:
        self.zi = signal.lfilter_zi(self.b, self.a)  # reset filter memory
        super().start_stream()