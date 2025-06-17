import pyaudio
import wave
import os
import time
import threading
import utils.settings
import utils.zw_logging

# Audio configuration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# Global audio variables
audio_interface = None
is_recording = False
latest_chat_frame_count = 0
recorded_frames = []

def initialize():
    """Initialize audio system"""
    global audio_interface
    
    try:
        audio_interface = pyaudio.PyAudio()
        utils.zw_logging.update_debug_log("Audio system initialized")
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Audio initialization failed: {e}")
        raise e


def record():
    """Record audio from microphone"""
    global is_recording, latest_chat_frame_count, recorded_frames
    
    if not audio_interface:
        raise RuntimeError("Audio system not initialized")
    
    is_recording = True
    recorded_frames = []
    
    try:
        # Open microphone stream
        stream = audio_interface.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        print("Recording... Press any key to stop.")
        
        # Record until silence detected or manual stop
        silence_threshold = 500
        silence_duration = 0
        max_silence = 2.0  # seconds
        
        while is_recording:
            data = stream.read(CHUNK, exception_on_overflow=False)
            recorded_frames.append(data)
            
            # Simple silence detection
            audio_level = max(data)
            if audio_level < silence_threshold:
                silence_duration += CHUNK / RATE
                if silence_duration > max_silence:
                    break
            else:
                silence_duration = 0
        
        stream.stop_stream()
        stream.close()
        
        latest_chat_frame_count = len(recorded_frames)
        
        # Save recording to file
        output_file = "temp_recording.wav"
        save_audio_frames(recorded_frames, output_file)
        
        utils.zw_logging.update_debug_log(f"Audio recorded: {latest_chat_frame_count} frames")
        return output_file
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Recording error: {e}")
        raise e
    finally:
        is_recording = False


def save_audio_frames(frames, filename):
    """Save recorded audio frames to file"""
    try:
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio_interface.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error saving audio: {e}")
        raise e


def stop_recording():
    """Stop current recording"""
    global is_recording
    is_recording = False


def get_latest_frame_count():
    """Get frame count of latest recording"""
    return latest_chat_frame_count


def is_audio_recording():
    """Check if currently recording"""
    return is_recording


def cleanup():
    """Clean up audio resources"""
    global audio_interface
    
    if audio_interface:
        try:
            audio_interface.terminate()
            utils.zw_logging.update_debug_log("Audio system cleaned up")
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Audio cleanup error: {e}")


# Auto-initialize on import
try:
    initialize()
except Exception as e:
    print(f"Warning: Audio initialization failed: {e}")
