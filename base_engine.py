import logging
import queue

import numpy as np
import scipy.io.wavfile as wavfile
import sounddevice as sd
from scipy import signal

logger = logging.getLogger(__name__)


class BaseAudioEngine:
    """
    Shared foundation for all audio engines.
    Owns all recording state, visual queue, and stream lifecycle.
    Subclasses must implement: _audio_callback, start_stream (for engine-specific setup).
    """

    def __init__(self):
        self.mic_id = None
        self.speaker_id = None
        self.virtual_output_id = None
        self.stream = None
        self.monitor_stream = None
        self.is_running = False
        self.is_engaged = False
        self.loopback_active = False

        self.sample_rate = 48000
        self.chunk_size = 4096

        self.output_gain_db = 0.0
        self.output_gain = 1.0

        # Post-processing filters
        shelf_b, shelf_a = self._make_high_shelf(7000, 2.5, self.sample_rate)
        self.shelf_b, self.shelf_a = shelf_b, shelf_a
        self.shelf_zi = signal.lfilter_zi(shelf_b, shelf_a)

        peak_b, peak_a = self._make_peaking_eq(3500, 1.5, 1.5, self.sample_rate)
        self.peak_b, self.peak_a = peak_b, peak_a
        self.peak_zi = signal.lfilter_zi(peak_b, peak_a)

        self.is_recording = False
        self.record_path = ""
        self.record_buffer = []

        self.visual_queue = queue.Queue(maxsize=15)

    def stop_and_save_recording(self):
        """Stop recording and flush buffer to disk."""
        self.is_recording = False
        if self.record_buffer and self.record_path:
            try:
                full_audio = np.concatenate(self.record_buffer)
                wavfile.write(self.record_path, self.sample_rate, full_audio)
                logger.info("File saved: %s", self.record_path)
            except OSError as e:
                logger.warning("Failed to save recording: %s", e)
        else:
            logger.info("Nothing to save.")
        self.record_buffer = []

    def _push_to_visual_queue(self, raw: np.ndarray, clean: np.ndarray):
        if self.visual_queue.full():
            try:
                self.visual_queue.get_nowait()
            except queue.Empty:
                pass
        try:
            self.visual_queue.put_nowait((raw, clean))
        except queue.Full:
            pass

    def start_stream(self):
        self.is_running = True
        if not self.is_recording:
            self.record_buffer = []

        self.stream = sd.Stream(
            device=(self.mic_id, self.virtual_output_id),
            samplerate=self.sample_rate,
            channels=1,
            blocksize=self.chunk_size,
            dtype=np.float32,
            callback=self._audio_callback,
        )
        self.stream.start()
        if self.speaker_id is not None:
            self.monitor_stream = sd.OutputStream(
                device=self.speaker_id,
                samplerate=self.sample_rate,
                channels=2,
                dtype=np.float32,
                blocksize=self.chunk_size,
            )
            self.monitor_stream.start()

    def _write_monitor(self, audio: np.ndarray):
        if not self.loopback_active:
            return

        if not self.monitor_stream:
            return

        try:
            stereo_audio = np.column_stack((audio, audio)).astype(np.float32)
            self.monitor_stream.write(stereo_audio)
        except Exception as e:
            logger.warning(f"Monitor stream write error: {e}")

    def stop_stream(self):
        self.is_running = False
        if self.is_recording:
            self.stop_and_save_recording()
        if self.monitor_stream:
            self.monitor_stream.stop()
            self.monitor_stream.close()
            self.monitor_stream = None
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None          

    @staticmethod
    def _make_high_shelf(freq, gain_db, fs):
        from scipy import signal
        A = 10 ** (gain_db / 40)
        w0 = 2 * np.pi * freq / fs
        cos_w0 = np.cos(w0)
        sin_w0 = np.sin(w0)
        alpha = sin_w0 / 2 * np.sqrt((A + 1/A) * (1/0.9 - 1) + 2)
        b0 =      A*((A+1) + (A-1)*cos_w0 + 2*np.sqrt(A)*alpha)
        b1 = -2*A*((A-1) + (A+1)*cos_w0)
        b2 =      A*((A+1) + (A-1)*cos_w0 - 2*np.sqrt(A)*alpha)
        a0 =         (A+1) - (A-1)*cos_w0 + 2*np.sqrt(A)*alpha
        a1 =    2*( (A-1) - (A+1)*cos_w0)
        a2 =         (A+1) - (A-1)*cos_w0 - 2*np.sqrt(A)*alpha
        return np.array([b0,b1,b2])/a0, np.array([1, a1/a0, a2/a0])

    @staticmethod
    def _make_peaking_eq(freq, gain_db, Q, fs):
        from scipy import signal
        A = 10 ** (gain_db / 40)
        w0 = 2 * np.pi * freq / fs
        alpha = np.sin(w0) / (2 * Q)
        b0 =   1 + alpha*A
        b1 =  -2 * np.cos(w0)
        b2 =   1 - alpha*A
        a0 =   1 + alpha/A
        a1 =  -2 * np.cos(w0)
        a2 =   1 - alpha/A
        return np.array([b0,b1,b2])/a0, np.array([1, a1/a0, a2/a0])

    def _apply_post_processing(self, audio: np.ndarray) -> np.ndarray:
        from scipy import signal
        # High shelf — presence recovery
        audio, self.shelf_zi = signal.lfilter(self.shelf_b, self.shelf_a, audio, zi=self.shelf_zi)
        # Peaking EQ — crispness
        audio, self.peak_zi = signal.lfilter(self.peak_b, self.peak_a, audio, zi=self.peak_zi)
        return audio.astype(np.float32)

    def _audio_callback(self, indata, outdata, frames, time, status):
        raise NotImplementedError