import sounddevice as sd
import numpy as np

MIC_IN_ID = 11
EAR_OUT_ID = 13

SAMPLE_RATE = 44100  
CHUNK_SIZE = 1024    

NOISE_THRESHOLD = 0.008  # Tweak this to clear your room's background hum

# --- ADVANCED SMOOTHING CONFIG ---
current_gain = 0.0  

# Attack: How fast the gate snaps open (1.0 = instant, lower = slight fade-in)
ATTACK_FACTOR = 0.40  

# Release: How slowly the gate fades out (Lower = longer, gentler tail)
RELEASE_FACTOR = 0.10  

def audio_callback(indata, outdata, frames, time, status):
    global current_gain
    
    if status:
        print(status)
        
    # 1. Calculate loudness (RMS)
    rms = np.sqrt(np.mean(indata**2))
    
    # 2. Determine target state
    target_gain = 1.0 if rms >= NOISE_THRESHOLD else 0.0
    
    # 3. Store the previous gain before updating
    old_gain = current_gain
    
    # 4. Asymmetric Logic: Choose Attack speed vs Release speed
    if target_gain > old_gain:
        # Opening the gate: Snap open fast!
        current_gain = (ATTACK_FACTOR * target_gain) + ((1 - ATTACK_FACTOR) * old_gain)
    else:
        # Closing the gate: Fade away slowly
        current_gain = (RELEASE_FACTOR * target_gain) + ((1 - RELEASE_FACTOR) * old_gain)
        
    # 5. Vectorized Ramping: Create a smooth slope of 1,024 values from old to new
    # This completely eliminates "zipper noise" or chunk-edge banding
    gain_ramp = np.linspace(old_gain, current_gain, CHUNK_SIZE).reshape(-1, 1)
    
    # 6. Apply the smooth ramp element-wise across the array
    outdata[:] = indata * gain_ramp

print("Active: Studio-Smooth Asymmetric Noise Gate")
print("Press Ctrl+C to stop...")

try:
    with sd.Stream(device=(MIC_IN_ID,EAR_OUT_ID),samplerate=SAMPLE_RATE, channels=1, blocksize=CHUNK_SIZE, callback=audio_callback):
        while True:
            sd.sleep(200)
except KeyboardInterrupt:
    print("\nAudio stream stopped.")