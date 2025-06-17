"""
Hangout Mode - Advanced conversation mode with intelligent response timing
Provides natural conversation flow with decision-making on when and how to respond
"""

import os
import json
import time
import threading
import random
from typing import Dict, List, Any, Optional
import utils.zw_logging
import utils.cane_lib
import utils.volume_listener
import utils.camera
import API.gemini_controller

# Hangout mode variables
hangout_enabled = False
is_hangout_active = False
hangout_personality = "balanced"
response_delay_min = 1.0
response_delay_max = 5.0
thinking_keywords = []
vision_keywords = []
interrupt_enabled = True
interrupt_phrases = []
hangout_thread = None

def initialize():
    """Initialize hangout mode system"""
    global hangout_enabled
    
    hangout_enabled = os.getenv("HANGOUT_ENABLED", "true").lower() == "true"
    
    if not hangout_enabled:
        utils.zw_logging.update_debug_log("Hangout mode disabled")
        return
    
    load_hangout_config()
    utils.zw_logging.update_debug_log("Hangout mode initialized")


def load_hangout_config():
    """Load hangout mode configuration"""
    global thinking_keywords, vision_keywords, interrupt_phrases
    global hangout_personality, response_delay_min, response_delay_max
    
    config_path = "Configurables/Hangout/hangout_config.json"
    
    try:
        if os.path.exists(config_path):
            config = utils.cane_lib.safe_json_load(config_path, {})
        else:
            create_default_hangout_config(config_path)
            config = utils.cane_lib.safe_json_load(config_path, {})
        
        # Load configuration values
        thinking_keywords = config.get("thinking_keywords", [])
        vision_keywords = config.get("vision_keywords", [])
        interrupt_phrases = config.get("interrupt_phrases", [])
        hangout_personality = config.get("personality", "balanced")
        response_delay_min = config.get("response_delay_min", 1.0)
        response_delay_max = config.get("response_delay_max", 5.0)
        
        utils.zw_logging.update_debug_log("Hangout configuration loaded")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error loading hangout config: {e}")


def create_default_hangout_config(path: str):
    """Create default hangout configuration"""
    utils.cane_lib.ensure_directory(os.path.dirname(path))
    
    default_config = {
        "personality": "balanced",
        "response_delay_min": 1.0,
        "response_delay_max": 5.0,
        "thinking_keywords": [
            "think about",
            "ponder",
            "consider",
            "wonder",
            "reflect",
            "contemplate",
            "muse",
            "deliberate"
        ],
        "vision_keywords": [
            "look at this",
            "see this",
            "check this out",
            "camera",
            "picture",
            "photo",
            "image",
            "visual",
            "show you"
        ],
        "interrupt_phrases": [
            "wait",
            "hold on",
            "stop",
            "pause",
            "interrupt"
        ],
        "personality_settings": {
            "quiet": {
                "description": "Responds less frequently, waits longer",
                "response_chance": 0.6,
                "delay_multiplier": 1.5,
                "thinking_chance": 0.3
            },
            "balanced": {
                "description": "Normal response behavior",
                "response_chance": 0.8,
                "delay_multiplier": 1.0,
                "thinking_chance": 0.2
            },
            "engaged": {
                "description": "Responds more frequently and quickly",
                "response_chance": 0.9,
                "delay_multiplier": 0.7,
                "thinking_chance": 0.4
            },
            "chatty": {
                "description": "Very responsive, minimal delays",
                "response_chance": 0.95,
                "delay_multiplier": 0.5,
                "thinking_chance": 0.5
            }
        }
    }
    
    utils.cane_lib.safe_json_save(path, default_config)
    utils.zw_logging.update_debug_log(f"Created default hangout config: {path}")


def start_hangout_mode():
    """Start hangout mode"""
    global is_hangout_active, hangout_thread
    
    if not hangout_enabled or is_hangout_active:
        return False
    
    is_hangout_active = True
    
    # Start hangout processing thread
    hangout_thread = threading.Thread(target=hangout_main_loop)
    hangout_thread.daemon = True
    hangout_thread.start()
    
    # Start volume monitoring for conversation detection
    utils.volume_listener.start_volume_monitoring()
    
    utils.zw_logging.update_debug_log("Hangout mode started")
    return True


def stop_hangout_mode():
    """Stop hangout mode"""
    global is_hangout_active
    
    is_hangout_active = False
    utils.volume_listener.stop_volume_monitoring()
    
    utils.zw_logging.update_debug_log("Hangout mode stopped")


def hangout_main_loop():
    """Main hangout mode processing loop"""
    while is_hangout_active:
        try:
            # Check for voice activity
            if utils.volume_listener.is_volume_above_threshold():
                process_hangout_input()
            
            time.sleep(0.1)
            
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Hangout loop error: {e}")
            time.sleep(1)


def process_hangout_input():
    """Process input during hangout mode"""
    try:
        # Record and transcribe input
        import utils.audio
        import utils.transcriber_translate
        
        audio_file = utils.audio.record()
        transcript = utils.transcriber_translate.transcribe_voice_to_text(audio_file)
        
        if not transcript or len(transcript.strip()) < 2:
            return
        
        utils.zw_logging.update_debug_log(f"Hangout input: {transcript}")
        
        # Decide how to respond
        response_decision = decide_response_behavior(transcript)
        
        if response_decision["should_respond"]:
            execute_hangout_response(transcript, response_decision)
        
        # Clean up audio file
        try:
            os.remove(audio_file)
        except:
            pass
            
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Hangout input processing error: {e}")


def decide_response_behavior(message: str) -> Dict[str, Any]:
    """Decide how to respond to hangout input"""
    decision = {
        "should_respond": True,
        "response_type": "immediate",
        "delay": 0.0,
        "should_think": False,
        "should_use_camera": False,
        "response_style": "normal"
    }
    
    try:
        # Load personality settings
        config = utils.cane_lib.safe_json_load("Configurables/Hangout/hangout_config.json", {})
        personality_settings = config.get("personality_settings", {})
        current_personality = personality_settings.get(hangout_personality, {})
        
        # Check response probability
        response_chance = current_personality.get("response_chance", 0.8)
        if random.random() > response_chance:
            decision["should_respond"] = False
            return decision
        
        # Check for thinking keywords
        thinking_chance = current_personality.get("thinking_chance", 0.2)
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in thinking_keywords):
            decision["should_think"] = True
            decision["response_type"] = "thinking"
            decision["delay"] = random.uniform(2.0, 5.0)
        elif random.random() < thinking_chance:
            decision["should_think"] = True
            decision["delay"] = random.uniform(1.0, 3.0)
        
        # Check for vision keywords
        if any(keyword in message_lower for keyword in vision_keywords):
            decision["should_use_camera"] = True
            decision["response_type"] = "visual"
            decision["delay"] = random.uniform(1.0, 2.0)
        
        # Apply personality delay multiplier
        delay_multiplier = current_personality.get("delay_multiplier", 1.0)
        base_delay = random.uniform(response_delay_min, response_delay_max)
        decision["delay"] = max(decision["delay"], base_delay * delay_multiplier)
        
        return decision
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Response decision error: {e}")
        return decision


def execute_hangout_response(message: str, decision: Dict[str, Any]):
    """Execute the decided response behavior"""
    try:
        # Apply delay if specified
        if decision.get("delay", 0) > 0:
            time.sleep(decision["delay"])
        
        # Handle thinking response
        if decision.get("should_think", False):
            thinking_prompt = f"The user said: '{message}'. Think about this and provide a thoughtful response."
            API.gemini_controller.send_message(thinking_prompt)
        
        # Handle visual response
        elif decision.get("should_use_camera", False):
            visual_response = handle_visual_request(message)
            if visual_response:
                # Visual response was handled
                return
        
        # Normal response
        else:
            response_prompt = f"In hangout mode, respond naturally to: '{message}'"
            API.gemini_controller.send_message(response_prompt)
        
        # Get and speak response
        response = API.gemini_controller.get_last_response()
        if response:
            import utils.voice
            utils.voice.speak_line(response)
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Hangout response execution error: {e}")


def handle_visual_request(message: str) -> bool:
    """Handle requests that involve using the camera"""
    try:
        # Take a photo
        image_path = utils.camera.capture_image()
        
        if not image_path:
            # No camera available
            fallback_response = "I'd love to look, but I can't access the camera right now."
            import utils.voice
            utils.voice.speak_line(fallback_response)
            return True
        
        # Process image with AI
        visual_prompt = f"The user said '{message}' and I'm looking at an image. Describe what I see and respond appropriately."
        visual_response = utils.camera.process_image_with_ai(image_path, visual_prompt)
        
        # Speak the response
        import utils.voice
        utils.voice.speak_line(visual_response)
        
        return True
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Visual request error: {e}")
        return False


def check_for_interruption(message: str) -> bool:
    """Check if message contains interruption phrases"""
    if not interrupt_enabled:
        return False
    
    message_lower = message.lower()
    char_name = os.getenv("CHAR_NAME", "aria").lower()
    
    # Check for interrupt patterns
    for phrase in interrupt_phrases:
        if phrase.lower() in message_lower and char_name in message_lower:
            return True
    
    return False


def set_hangout_personality(personality: str) -> bool:
    """Set hangout personality mode"""
    global hangout_personality
    
    valid_personalities = ["quiet", "balanced", "engaged", "chatty"]
    
    if personality in valid_personalities:
        hangout_personality = personality
        utils.zw_logging.update_debug_log(f"Hangout personality set to: {personality}")
        return True
    else:
        utils.zw_logging.update_debug_log(f"Invalid hangout personality: {personality}")
        return False


def get_hangout_status():
    """Get hangout mode status"""
    return {
        "enabled": hangout_enabled,
        "active": is_hangout_active,
        "personality": hangout_personality,
        "interrupt_enabled": interrupt_enabled,
        "thinking_keywords_count": len(thinking_keywords),
        "vision_keywords_count": len(vision_keywords)
    }


def add_thinking_keyword(keyword: str):
    """Add a thinking trigger keyword"""
    global thinking_keywords
    
    if keyword.lower() not in [kw.lower() for kw in thinking_keywords]:
        thinking_keywords.append(keyword.lower())
        save_hangout_config()
        utils.zw_logging.update_debug_log(f"Added thinking keyword: {keyword}")


def add_vision_keyword(keyword: str):
    """Add a vision trigger keyword"""
    global vision_keywords
    
    if keyword.lower() not in [kw.lower() for kw in vision_keywords]:
        vision_keywords.append(keyword.lower())
        save_hangout_config()
        utils.zw_logging.update_debug_log(f"Added vision keyword: {keyword}")


def save_hangout_config():
    """Save hangout configuration"""
    try:
        config_path = "Configurables/Hangout/hangout_config.json"
        existing_config = utils.cane_lib.safe_json_load(config_path, {})
        
        # Update with current values
        existing_config.update({
            "thinking_keywords": thinking_keywords,
            "vision_keywords": vision_keywords,
            "interrupt_phrases": interrupt_phrases,
            "personality": hangout_personality,
            "response_delay_min": response_delay_min,
            "response_delay_max": response_delay_max
        })
        
        utils.cane_lib.safe_json_save(config_path, existing_config)
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error saving hangout config: {e}")


def toggle_hangout_mode():
    """Toggle hangout mode on/off"""
    if is_hangout_active:
        stop_hangout_mode()
        return False
    else:
        return start_hangout_mode()


# Initialize if enabled
if hangout_enabled:
    initialize()
