import os
import threading
import time
import pyttsx3
import utils.settings
import utils.zw_logging

# Global voice variables
tts_engine = None
is_speaking = False
should_stop_speaking = False

def initialize():
    """Initialize text-to-speech engine"""
    global tts_engine
    
    try:
        tts_engine = pyttsx3.init()
        
        # Configure voice settings
        voices = tts_engine.getProperty('voices')
        voice_id = os.getenv("VOICE_ID", "0")
        
        if voices and len(voices) > int(voice_id):
            tts_engine.setProperty('voice', voices[int(voice_id)].id)
        
        # Set speech rate and volume
        tts_engine.setProperty('rate', int(os.getenv("VOICE_RATE", "200")))
        tts_engine.setProperty('volume', float(os.getenv("VOICE_VOLUME", "0.9")))
        
        utils.zw_logging.update_debug_log("TTS engine initialized")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"TTS initialization failed: {e}")
        print(f"Warning: Text-to-speech may not work properly: {e}")


def speak_line(text: str, refuse_pause: bool = False):
    """Speak the given text"""
    global is_speaking, should_stop_speaking
    
    if not tts_engine:
        utils.zw_logging.update_debug_log("TTS engine not available")
        return
    
    if not text or text.strip() == "":
        return
    
    # Clean text for speech
    clean_text = clean_text_for_speech(text)
    
    if not clean_text:
        return
    
    is_speaking = True
    should_stop_speaking = False
    
    try:
        # Check for interruption before speaking
        if should_stop_speaking:
            return
        
        # Speak the text
        tts_engine.say(clean_text)
        
        # Run the speech in a separate thread to allow interruption
        def run_speech():
            global is_speaking
            try:
                tts_engine.runAndWait()
            except Exception as e:
                utils.zw_logging.update_debug_log(f"Speech error: {e}")
            finally:
                is_speaking = False
        
        speech_thread = threading.Thread(target=run_speech)
        speech_thread.daemon = True
        speech_thread.start()
        
        # Wait for speech to complete or be interrupted
        while speech_thread.is_alive() and not should_stop_speaking:
            time.sleep(0.01)
        
        if should_stop_speaking:
            force_cut_voice()
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Speech error: {e}")
        is_speaking = False


def clean_text_for_speech(text: str) -> str:
    """Clean text for better speech synthesis"""
    if not text:
        return ""
    
    # Remove asterisks (actions)
    cleaned = text.replace("*", "")
    
    # Remove certain symbols that don't speak well
    cleaned = cleaned.replace("~", "")
    cleaned = cleaned.replace("#", "")
    cleaned = cleaned.replace("@", "at")
    
    # Handle multiple punctuation
    cleaned = cleaned.replace("!!!", "!")
    cleaned = cleaned.replace("???", "?")
    cleaned = cleaned.replace("...", ".")
    
    # Remove excessive whitespace
    cleaned = " ".join(cleaned.split())
    
    return cleaned.strip()


def set_speaking(speaking: bool):
    """Set speaking state"""
    global is_speaking
    is_speaking = speaking


def check_if_speaking() -> bool:
    """Check if currently speaking"""
    return is_speaking


def force_cut_voice():
    """Force stop current speech"""
    global should_stop_speaking, is_speaking
    
    should_stop_speaking = True
    
    try:
        if tts_engine:
            tts_engine.stop()
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error stopping speech: {e}")
    
    is_speaking = False


def adjust_volume(delta: float):
    """Adjust voice volume by delta (-1.0 to 1.0)"""
    try:
        if tts_engine:
            current_volume = tts_engine.getProperty('volume')
            new_volume = max(0.0, min(1.0, current_volume + delta))
            tts_engine.setProperty('volume', new_volume)
            utils.zw_logging.update_debug_log(f"Voice volume adjusted to: {new_volume}")
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Volume adjustment error: {e}")


def get_available_voices():
    """Get list of available voices"""
    try:
        if tts_engine:
            voices = tts_engine.getProperty('voices')
            return [(i, voice.name) for i, voice in enumerate(voices)]
        return []
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error getting voices: {e}")
        return []


def set_voice(voice_index: int):
    """Set voice by index"""
    try:
        if tts_engine:
            voices = tts_engine.getProperty('voices')
            if 0 <= voice_index < len(voices):
                tts_engine.setProperty('voice', voices[voice_index].id)
                utils.zw_logging.update_debug_log(f"Voice set to: {voices[voice_index].name}")
                return True
        return False
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error setting voice: {e}")
        return False


# Auto-initialize on import
try:
    initialize()
except Exception as e:
    print(f"Warning: Voice initialization failed: {e}")
