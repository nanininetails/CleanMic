import sounddevice as sd
import numpy as np
import queue
import scipy.io.wavfile as wavfile
from pyrnnoise import RNNoise

class AudioEngine:
    def __init__(self):
        self.mic_id = None
        self.speaker_id = None
        self.stream = None
        self.is_running = False
        
        # RNNoise STRICTLY requires 48kHz and 10ms chunks (480 samples)
        self.sample_rate = 48000
        self.chunk_size = 480 
        
        # Instantiate the RNNoise AI
        self.denoiser = RNNoise(sample_rate=self.sample_rate)
        
        # GUI Compatibility Variables (The AI handles this natively now, 
        # but the GUI sliders still need these variables to exist so they don't crash)
        self.scan_time_seconds = 4.0
        self.scrub_power = 0.98
        self.hunting_focus = 2.0
        self.word_fade_ms = 90
        self.voice_shield_hz = 400
        
        self.record_armed = False
        self.is_recording = False
        self.record_path = ""
        self.record_buffer = []
        self.visual_queue = queue.Queue(maxsize=15)

    def stop_and_save_recording(self):
        self.is_recording = False
        self.record_armed = False
        if self.record_buffer and self.record_path:
            try:
                full_audio = np.concatenate(self.record_buffer)
                wavfile.write(self.record_path, self.sample_rate, full_audio)
                print(f"[RNNoise] File saved: {self.record_path}")
            except Exception as e:
                print(f"[Error] {e}")
        self.record_buffer = []

    def _audio_callback(self, indata, outdata, frames, time, status):
        if not self.is_running:
            outdata.fill(0)
            return

        raw_audio = indata[:, 0].copy()

        try:
            # RNNoise instantly processes the 10ms frame and returns a speech probability and the clean wave
            speech_prob, clean_audio = self.denoiser.denoise_frame(raw_audio)
            
            clean_audio = np.clip(clean_audio, -1.0, 1.0)
            outdata[:] = clean_audio.reshape(-1, 1).astype(np.float32)
            
            if self.is_recording:
                self.record_buffer.append(clean_audio.copy())
            self._push_to_visual_queue(raw_audio, clean_audio)
        except Exception as e:
            outdata[:] = indata
            self._push_to_visual_queue(raw_audio, raw_audio)

    def _push_to_visual_queue(self, raw, clean):
        if self.visual_queue.full():
            try: self.visual_queue.get_nowait()
            except queue.Empty: pass
        try: self.visual_queue.put_nowait((raw, clean))
        except queue.Full: pass

    def start_stream(self):
        self.is_running = True
        if self.record_armed:
            self.record_buffer = []
            self.is_recording = True
            
        self.stream = sd.Stream(
            device=(self.mic_id, self.speaker_id),
            samplerate=self.sample_rate,
            channels=1,
            blocksize=self.chunk_size,
            dtype=np.float32,
            callback=self._audio_callback
        )
        self.stream.start()

    def stop_stream(self):
        self.is_running = False
        if self.is_recording:
            self.stop_and_save_recording()
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None