import whisper
import os
import threading
import time
import utils.settings
import utils.zw_logging

# Global transcription variables
whisper_model = None
transcription_chunks = []
chunky_request = None
is_transcribing = False

def initialize():
    """Initialize Whisper model"""
    global whisper_model
    
    model_size = os.getenv("WHISPER_MODEL", "base")
    
    try:
        utils.zw_logging.update_debug_log(f"Loading Whisper model: {model_size}")
        whisper_model = whisper.load_model(model_size)
        utils.zw_logging.update_debug_log("Whisper model loaded successfully")
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Whisper model loading failed: {e}")
        # Fallback to base model
        try:
            whisper_model = whisper.load_model("base")
            utils.zw_logging.update_debug_log("Loaded fallback Whisper base model")
        except Exception as e2:
            utils.zw_logging.update_debug_log(f"Fallback model loading failed: {e2}")
            raise e2


def transcribe_voice_to_text(audio_file: str) -> str:
    """Transcribe audio file to text"""
    global is_transcribing
    
    if not whisper_model:
        raise RuntimeError("Whisper model not initialized")
    
    is_transcribing = True
    
    try:
        # Check if chunked transcription is available
        if transcription_chunks:
            # Use chunked transcription
            result_text = " ".join(transcription_chunks)
            clear_transcription_chunks()
        else:
            # Standard transcription
            result = whisper_model.transcribe(
                audio_file,
                language="en" if "en" in os.getenv("WHISPER_MODEL", "base") else None,
                temperature=0.0  # Reduce hallucinations
            )
            result_text = result["text"].strip()
        
        utils.zw_logging.update_debug_log(f"Transcription result: {len(result_text)} characters")
        return result_text
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Transcription error: {e}")
        return "Sorry, I couldn't understand that."
    finally:
        is_transcribing = False


def start_chunked_transcription(audio_file: str):
    """Start chunked transcription in background"""
    global chunky_request
    
    def transcribe_chunks():
        global transcription_chunks, chunky_request
        
        try:
            # This is a simplified version - real implementation would 
            # process audio in chunks as it's being recorded
            result = whisper_model.transcribe(audio_file, temperature=0.0)
            
            # Split result into chunks (simulate chunk processing)
            words = result["text"].split()
            chunk_size = max(1, len(words) // 5)  # 5 chunks
            
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                transcription_chunks.append(chunk)
                time.sleep(0.1)  # Simulate processing time
                
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Chunked transcription error: {e}")
        finally:
            chunky_request = None
    
    chunky_request = threading.Thread(target=transcribe_chunks)
    chunky_request.daemon = True
    chunky_request.start()


def clear_transcription_chunks():
    """Clear transcription chunks"""
    global transcription_chunks
    transcription_chunks.clear()


def is_transcription_in_progress():
    """Check if transcription is in progress"""
    return is_transcribing or chunky_request is not None


def get_transcription_chunks():
    """Get current transcription chunks"""
    return transcription_chunks.copy()


# Auto-initialize on import
try:
    initialize()
except Exception as e:
    print(f"Warning: Whisper initialization failed: {e}")
    whisper_model = None
