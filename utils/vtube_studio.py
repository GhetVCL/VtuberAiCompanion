import json
import asyncio
import threading
import time
import re
import os
import utils.settings
import utils.zw_logging

# VTube Studio integration variables
current_emote_string = ""
is_connected = False
websocket_connection = None
emote_mappings = {}

def initialize():
    """Initialize VTube Studio connection"""
    global is_connected
    
    if not utils.settings.vtube_enabled:
        return
    
    load_emote_mappings()
    
    # Start connection in background thread
    connection_thread = threading.Thread(target=start_connection)
    connection_thread.daemon = True
    connection_thread.start()


def load_emote_mappings():
    """Load emote mappings from configuration"""
    global emote_mappings
    
    config_path = "Configurables/VTubeStudio/emote_mappings.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            emote_mappings = json.load(f)
    except FileNotFoundError:
        create_default_emote_mappings(config_path)
        load_emote_mappings()
    except json.JSONDecodeError as e:
        utils.zw_logging.update_debug_log(f"Invalid emote mapping JSON: {e}")
        create_default_emote_mappings(config_path)


def create_default_emote_mappings(path: str):
    """Create default emote mappings"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    default_mappings = {
        "happy": {
            "keywords": ["happy", "smile", "joy", "glad", "cheerful"],
            "hotkey": "1"
        },
        "sad": {
            "keywords": ["sad", "cry", "unhappy", "upset", "disappointed"],
            "hotkey": "2"
        },
        "surprised": {
            "keywords": ["surprised", "wow", "amazing", "shocked"],
            "hotkey": "3"
        },
        "angry": {
            "keywords": ["angry", "mad", "frustrated", "annoyed"],
            "hotkey": "4"
        },
        "confused": {
            "keywords": ["confused", "huh", "what", "unclear"],
            "hotkey": "5"
        },
        "excited": {
            "keywords": ["excited", "yay", "awesome", "fantastic"],
            "hotkey": "6"
        },
        "thinking": {
            "keywords": ["think", "consider", "wonder", "ponder"],
            "hotkey": "7"
        },
        "greeting": {
            "keywords": ["hello", "hi", "greetings", "welcome"],
            "hotkey": "8"
        }
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(default_mappings, f, ensure_ascii=False, indent=2)
    
    utils.zw_logging.update_debug_log(f"Created default emote mappings: {path}")


def start_connection():
    """Start VTube Studio WebSocket connection"""
    global is_connected
    
    try:
        # This is a placeholder for actual VTube Studio API connection
        # Real implementation would use the VTube Studio API protocol
        utils.zw_logging.update_debug_log("VTube Studio connection started (placeholder)")
        is_connected = True
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"VTube Studio connection failed: {e}")
        is_connected = False


def set_emote_string(message: str):
    """Set the current message for emote analysis"""
    global current_emote_string
    current_emote_string = message.lower()


def check_emote_string():
    """Check current message for emote triggers"""
    if not current_emote_string or not is_connected:
        return
    
    try:
        # Check for emote keywords
        for emote_name, emote_data in emote_mappings.items():
            keywords = emote_data.get("keywords", [])
            
            for keyword in keywords:
                if keyword.lower() in current_emote_string:
                    trigger_emote(emote_name, emote_data.get("hotkey", ""))
                    break
        
        # Check for special expressions
        check_special_expressions()
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Emote checking error: {e}")


def check_special_expressions():
    """Check for special expressions and patterns"""
    message = current_emote_string
    
    # Check for emoticons
    if any(emoticon in message for emoticon in [":)", "^_^", ":D", "XD"]):
        trigger_emote("happy", "1")
    elif any(emoticon in message for emoticon in [":(", ";_;", "T_T"]):
        trigger_emote("sad", "2")
    elif any(emoticon in message for emoticon in [":o", "O_O", "@_@"]):
        trigger_emote("surprised", "3")
    
    # Check for special characters indicating emotion
    if "!" in message and len(re.findall(r"!", message)) >= 2:
        trigger_emote("excited", "6")
    elif "?" in message and len(re.findall(r"\?", message)) >= 2:
        trigger_emote("confused", "5")


def trigger_emote(emote_name: str, hotkey: str):
    """Trigger a specific emote"""
    try:
        if not is_connected:
            return
        
        # In a real implementation, this would send the hotkey to VTube Studio
        # For now, we'll just log it
        utils.zw_logging.update_debug_log(f"Emote triggered: {emote_name} (hotkey: {hotkey})")
        
        # Simulate emote trigger delay
        time.sleep(0.1)
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Emote trigger error: {e}")


def send_hotkey_to_vtube_studio(hotkey: str):
    """Send hotkey command to VTube Studio"""
    # Placeholder for actual VTube Studio API call
    # Real implementation would use the VTube Studio API
    utils.zw_logging.update_debug_log(f"Sending hotkey to VTube Studio: {hotkey}")


def set_idle_animation():
    """Set idle animation"""
    if is_connected:
        utils.zw_logging.update_debug_log("Setting idle animation")


def set_speaking_animation():
    """Set speaking animation"""
    if is_connected:
        utils.zw_logging.update_debug_log("Setting speaking animation")


def get_connection_status():
    """Get VTube Studio connection status"""
    return is_connected


def disconnect():
    """Disconnect from VTube Studio"""
    global is_connected, websocket_connection
    
    try:
        is_connected = False
        if websocket_connection:
            # Close connection
            websocket_connection = None
        utils.zw_logging.update_debug_log("Disconnected from VTube Studio")
    except Exception as e:
        utils.zw_logging.update_debug_log(f"VTube Studio disconnect error: {e}")


# Initialize if VTube Studio is enabled
if utils.settings.vtube_enabled:
    initialize()
