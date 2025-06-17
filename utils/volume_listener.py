import pyaudio
import numpy as np
import threading
import time
import utils.settings
import utils.zw_logging

# Volume monitoring variables
is_monitoring = False
current_volume = 0.0
volume_threshold = 0.1
monitoring_thread = None
audio_stream = None

def start_volume_monitoring():
    """Start monitoring audio volume levels"""
    global is_monitoring, monitoring_thread
    
    if is_monitoring:
        return
    
    is_monitoring = True
    monitoring_thread = threading.Thread(target=volume_monitoring_loop)
    monitoring_thread.daemon = True
    monitoring_thread.start()
    
    utils.zw_logging.update_debug_log("Volume monitoring started")


def volume_monitoring_loop():
    """Main volume monitoring loop"""
    global current_volume, audio_stream
    
    try:
        # Initialize PyAudio
        p = pyaudio.PyAudio()
        
        # Audio stream configuration
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        
        audio_stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        while is_monitoring:
            try:
                # Read audio data
                data = audio_stream.read(CHUNK, exception_on_overflow=False)
                
                # Convert to numpy array
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Calculate RMS volume
                current_volume = np.sqrt(np.mean(audio_data**2)) / 32768.0
                
                time.sleep(0.01)  # Small delay to prevent CPU overload
                
            except Exception as e:
                utils.zw_logging.update_debug_log(f"Volume monitoring error: {e}")
                time.sleep(0.1)
    
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Volume monitoring initialization error: {e}")
    
    finally:
        if audio_stream:
            audio_stream.stop_stream()
            audio_stream.close()
        if 'p' in locals():
            p.terminate()


def stop_volume_monitoring():
    """Stop volume monitoring"""
    global is_monitoring
    is_monitoring = False
    utils.zw_logging.update_debug_log("Volume monitoring stopped")


def get_current_volume():
    """Get current volume level"""
    return current_volume


def set_volume_threshold(threshold: float):
    """Set volume threshold for detection"""
    global volume_threshold
    volume_threshold = max(0.0, min(1.0, threshold))
    utils.zw_logging.update_debug_log(f"Volume threshold set to: {volume_threshold}")


def is_volume_above_threshold():
    """Check if current volume is above threshold"""
    return current_volume > volume_threshold


def get_volume_stats():
    """Get volume monitoring statistics"""
    return {
        "current_volume": current_volume,
        "threshold": volume_threshold,
        "is_monitoring": is_monitoring,
        "above_threshold": is_volume_above_threshold()
    }


def calibrate_volume_threshold():
    """Auto-calibrate volume threshold based on ambient noise"""
    if not is_monitoring:
        start_volume_monitoring()
    
    utils.zw_logging.update_debug_log("Starting volume threshold calibration...")
    
    # Collect volume samples for 3 seconds
    samples = []
    start_time = time.time()
    
    while time.time() - start_time < 3.0:
        samples.append(current_volume)
        time.sleep(0.1)
    
    if samples:
        # Set threshold to 3x the average ambient noise
        avg_ambient = np.mean(samples)
        new_threshold = min(0.5, avg_ambient * 3.0)
        set_volume_threshold(new_threshold)
        utils.zw_logging.update_debug_log(f"Volume threshold calibrated to: {new_threshold}")
        return new_threshold
    
    return volume_threshold
