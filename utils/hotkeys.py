import keyboard
import json
import os
import threading
import time
import utils.settings
import utils.zw_logging

# Global hotkey variables
hotkey_config = {}
input_stack = []
autochat_enabled = False
semi_auto_chat = False
speak_input_active = False

def initialize():
    """Initialize hotkey system"""
    load_hotkey_config()
    setup_hotkeys()
    utils.zw_logging.update_debug_log("Hotkey system initialized")


def load_hotkey_config():
    """Load hotkey configuration from JSON"""
    global hotkey_config
    
    config_path = "Configurables/Hotkeys/hotkeys.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            hotkey_config = json.load(f)
    except FileNotFoundError:
        create_default_hotkey_config(config_path)
        load_hotkey_config()
    except json.JSONDecodeError as e:
        utils.zw_logging.update_debug_log(f"Invalid hotkey config JSON: {e}")
        create_default_hotkey_config(config_path)
        load_hotkey_config()


def create_default_hotkey_config(path: str):
    """Create default hotkey configuration"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    default_config = {
        "chat": "space",
        "next": "n", 
        "redo": "r",
        "soft_reset": "delete",
        "alarm": "f1",
        "view_image": "f2",
        "blank": "f3",
        "hangout": "h",
        "autochat_toggle": "f4",
        "semi_auto_toggle": "q",
        "volume_up": "ctrl+up",
        "volume_down": "ctrl+down"
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, ensure_ascii=False, indent=2)
    
    utils.zw_logging.update_debug_log(f"Created default hotkey config: {path}")


def setup_hotkeys():
    """Set up keyboard listeners"""
    try:
        # Chat hotkey
        keyboard.add_hotkey(hotkey_config.get("chat", "space"), 
                          lambda: add_to_input_stack("CHAT"))
        
        # Next/regenerate hotkey
        keyboard.add_hotkey(hotkey_config.get("next", "n"), 
                          lambda: add_to_input_stack("NEXT"))
        
        # Redo hotkey
        keyboard.add_hotkey(hotkey_config.get("redo", "r"), 
                          lambda: add_to_input_stack("REDO"))
        
        # Soft reset hotkey
        keyboard.add_hotkey(hotkey_config.get("soft_reset", "delete"), 
                          lambda: add_to_input_stack("SOFT_RESET"))
        
        # Alarm hotkey
        keyboard.add_hotkey(hotkey_config.get("alarm", "f1"), 
                          lambda: add_to_input_stack("ALARM"))
        
        # View image hotkey
        keyboard.add_hotkey(hotkey_config.get("view_image", "f2"), 
                          lambda: add_to_input_stack("VIEW"))
        
        # Blank hotkey
        keyboard.add_hotkey(hotkey_config.get("blank", "f3"), 
                          lambda: add_to_input_stack("BLANK"))
        
        # Hangout mode hotkey
        keyboard.add_hotkey(hotkey_config.get("hangout", "h"), 
                          lambda: add_to_input_stack("Hangout"))
        
        # Autochat toggle
        keyboard.add_hotkey(hotkey_config.get("autochat_toggle", "f4"), 
                          toggle_autochat)
        
        # Semi-auto chat toggle
        keyboard.add_hotkey(hotkey_config.get("semi_auto_toggle", "q"), 
                          toggle_semi_auto_chat)
        
        utils.zw_logging.update_debug_log("Hotkeys registered successfully")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Hotkey setup failed: {e}")
        print(f"Warning: Some hotkeys may not work properly: {e}")


def add_to_input_stack(command: str):
    """Add command to input stack"""
    global input_stack
    input_stack.append(command)
    utils.zw_logging.update_debug_log(f"Hotkey pressed: {command}")


def chat_input_await():
    """Wait for and return next command from input stack"""
    global input_stack
    
    while True:
        if input_stack:
            command = input_stack.pop(0)
            return command
        
        # Check for autochat activation
        if autochat_enabled and should_activate_autochat():
            return "CHAT"
        
        time.sleep(0.01)


def should_activate_autochat():
    """Check if autochat should be activated based on voice activity"""
    # This would integrate with VAD (Voice Activity Detection)
    # For now, return False - implement VAD integration here
    return False


def toggle_autochat():
    """Toggle autochat mode"""
    global autochat_enabled
    autochat_enabled = not autochat_enabled
    print(f"Autochat {'enabled' if autochat_enabled else 'disabled'}")
    utils.zw_logging.update_debug_log(f"Autochat toggled: {autochat_enabled}")


def toggle_semi_auto_chat():
    """Toggle semi-auto chat mode"""
    global semi_auto_chat
    semi_auto_chat = not semi_auto_chat
    print(f"Semi-auto chat {'enabled' if semi_auto_chat else 'disabled'}")
    utils.zw_logging.update_debug_log(f"Semi-auto chat toggled: {semi_auto_chat}")


def get_autochat_toggle():
    """Get autochat state"""
    return autochat_enabled


def speak_input_toggle_from_ui():
    """Toggle speak input from UI"""
    global speak_input_active
    speak_input_active = not speak_input_active


def stack_wipe_inputs():
    """Clear input stack"""
    global input_stack
    input_stack.clear()


def cleanup():
    """Clean up hotkey system"""
    try:
        keyboard.unhook_all()
        utils.zw_logging.update_debug_log("Hotkeys cleaned up")
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Hotkey cleanup error: {e}")
