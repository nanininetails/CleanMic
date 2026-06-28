import logging
import numpy as np
from base_engine import BaseAudioEngine
import importlib.util
import sys
import os

if getattr(sys, 'frozen', False):
    _pyrnnoise_path = os.path.join(sys._MEIPASS, 'pyrnnoise', 'rnnoise.py')
else:
    _pyrnnoise_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'venv', 'Lib', 'site-packages', 'pyrnnoise', 'rnnoise.py'
    )

spec = importlib.util.spec_from_file_location('rnnoise', _pyrnnoise_path)

_rnnoise = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_rnnoise)
create = _rnnoise.create
destroy = _rnnoise.destroy
process_frame = _rnnoise.process_frame
FRAME_SIZE = _rnnoise.FRAME_SIZE

logger = logging.getLogger(__name__)

class AudioEngine(BaseAudioEngine):
    def __init__(self):
        super().__init__()
        self.chunk_size = 480
        self.denoise_state = create()
        self._was_engaged = False

        # Dummy tuning params — GUI drawer needs these to not crash
        self.scan_time_seconds = 4.0
        self.scrub_power = 0.98
        self.hunting_focus = 2.0
        self.word_fade_ms = 90
        self.voice_shield_hz = 400

    def _audio_callback(self, indata, outdata, frames, time, status):
        if status:
            logger.warning("Hardware warning: %s", status)
        if not self.is_running:
            outdata.fill(0)
            return

        raw = indata[:, 0].copy()

        if not self.is_engaged:
            if getattr(self, '_was_engaged', False):
                self.reset_denoiser()
                self._was_engaged = False
            gained = np.clip(indata * self.output_gain, -1.0, 1.0).astype(np.float32)
            outdata[:] = gained
            gained_raw = gained[:, 0].copy()
            self._write_monitor(gained_raw)
            if self.is_recording:
                self.record_buffer.append(gained_raw)
            self._push_to_visual_queue(raw, gained_raw)
            return

        self._was_engaged = True
        try:
            clean_int16, speech_prob = process_frame(self.denoise_state, raw)
            clean_audio = clean_int16.astype(np.float32) / 32768.0

            clean_audio = self._apply_post_processing(clean_audio)
            clean_audio *= self.output_gain
            clean_audio = np.clip(clean_audio, -1.0, 1.0)
            outdata[:] = clean_audio.reshape(-1, 1).astype(np.float32)
            self._write_monitor(clean_audio)
            if self.is_recording:
                self.record_buffer.append(clean_audio.copy())
            self._push_to_visual_queue(raw, clean_audio)

        except Exception as e:
            logger.warning("RNNoise error: %s", e)
            outdata[:] = indata
            self._write_monitor(raw)
            if self.is_recording:
                self.record_buffer.append(raw.copy())
            self._push_to_visual_queue(raw, raw)

    def start_stream(self) -> None:
        self.reset_denoiser()
        super().start_stream()
    
    def __del__(self):
        if hasattr(self, 'denoise_state') and self.denoise_state:
            destroy(self.denoise_state)
    
    def reset_denoiser(self):
        if hasattr(self, 'denoise_state') and self.denoise_state:
            destroy(self.denoise_state)
        self.denoise_state = create()