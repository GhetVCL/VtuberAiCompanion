"""
Gaming Control System - Handles gaming mode and game-specific interactions
Provides enhanced responses and controls for gaming scenarios
"""

import os
import json
import time
import threading
import pyautogui
from typing import Dict, List, Any, Optional
import utils.zw_logging
import utils.cane_lib
import utils.settings

# Gaming control variables
gaming_enabled = False
is_gaming_loop = False
current_game = None
game_profiles = {}
gaming_hotkeys = {}
last_gaming_action = 0
gaming_cooldown = 1.0

def initialize():
    """Initialize gaming control system"""
    global gaming_enabled
    
    gaming_enabled = utils.settings.gaming_enabled
    
    if not gaming_enabled:
        utils.zw_logging.update_debug_log("Gaming control disabled")
        return
    
    load_game_profiles()
    load_gaming_hotkeys()
    
    utils.zw_logging.update_debug_log("Gaming control system initialized")


def load_game_profiles():
    """Load game-specific profiles"""
    global game_profiles
    
    profiles_path = "Configurables/Gaming/game_profiles.json"
    
    try:
        if os.path.exists(profiles_path):
            game_profiles = utils.cane_lib.safe_json_load(profiles_path, {})
        else:
            create_default_game_profiles(profiles_path)
            game_profiles = utils.cane_lib.safe_json_load(profiles_path, {})
        
        utils.zw_logging.update_debug_log(f"Loaded {len(game_profiles)} game profiles")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error loading game profiles: {e}")
        game_profiles = {}


def create_default_game_profiles(path: str):
    """Create default game profiles"""
    utils.cane_lib.ensure_directory(os.path.dirname(path))
    
    default_profiles = {
        "minecraft": {
            "name": "Minecraft",
            "commands": {
                "move_forward": {"key": "w", "description": "Move forward"},
                "move_back": {"key": "s", "description": "Move backward"},
                "move_left": {"key": "a", "description": "Move left"},
                "move_right": {"key": "d", "description": "Move right"},
                "jump": {"key": "space", "description": "Jump"},
                "sneak": {"key": "shift", "description": "Sneak"},
                "inventory": {"key": "e", "description": "Open inventory"},
                "chat": {"key": "t", "description": "Open chat"}
            },
            "responses": {
                "death": ["Oh no! I died!", "That didn't go well...", "Let me try again!"],
                "achievement": ["Yay! Achievement unlocked!", "Nice! Got an achievement!", "Success!"],
                "low_health": ["I need to be careful, low health!", "Health is getting low!"],
                "night_time": ["It's getting dark, time to be careful!", "Night time - watch out for monsters!"]
            }
        },
        "fps_game": {
            "name": "FPS Game",
            "commands": {
                "move_forward": {"key": "w", "description": "Move forward"},
                "move_back": {"key": "s", "description": "Move backward"},
                "move_left": {"key": "a", "description": "Strafe left"},
                "move_right": {"key": "d", "description": "Strafe right"},
                "shoot": {"key": "mouse_left", "description": "Shoot"},
                "reload": {"key": "r", "description": "Reload weapon"},
                "crouch": {"key": "ctrl", "description": "Crouch"},
                "run": {"key": "shift", "description": "Run"}
            },
            "responses": {
                "kill": ["Got one!", "Enemy down!", "Nice shot!"],
                "death": ["I got eliminated!", "They got me!", "Respawning..."],
                "low_ammo": ["Need to reload!", "Running low on ammo!"],
                "enemy_spotted": ["Enemy spotted!", "Contact!", "Target acquired!"]
            }
        },
        "strategy_game": {
            "name": "Strategy Game",
            "commands": {
                "pause": {"key": "space", "description": "Pause game"},
                "speed_up": {"key": "+", "description": "Increase game speed"},
                "slow_down": {"key": "-", "description": "Decrease game speed"},
                "save": {"key": "ctrl+s", "description": "Save game"},
                "menu": {"key": "esc", "description": "Open menu"}
            },
            "responses": {
                "victory": ["Victory achieved!", "We won!", "Excellent strategy!"],
                "defeat": ["We lost this one...", "Need to adjust strategy", "Better luck next time"],
                "resource_low": ["Resources are running low!", "Need to gather more resources"],
                "enemy_attack": ["Under attack!", "Defend the base!", "Enemy approaching!"]
            }
        }
    }
    
    utils.cane_lib.safe_json_save(path, default_profiles)
    utils.zw_logging.update_debug_log(f"Created default game profiles: {path}")


def load_gaming_hotkeys():
    """Load gaming-specific hotkeys"""
    global gaming_hotkeys
    
    hotkeys_path = "Configurables/Gaming/gaming_hotkeys.json"
    
    try:
        if os.path.exists(hotkeys_path):
            gaming_hotkeys = utils.cane_lib.safe_json_load(hotkeys_path, {})
        else:
            create_default_gaming_hotkeys(hotkeys_path)
            gaming_hotkeys = utils.cane_lib.safe_json_load(hotkeys_path, {})
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error loading gaming hotkeys: {e}")
        gaming_hotkeys = {}


def create_default_gaming_hotkeys(path: str):
    """Create default gaming hotkeys"""
    utils.cane_lib.ensure_directory(os.path.dirname(path))
    
    default_hotkeys = {
        "gaming_mode_toggle": "f5",
        "quick_action_1": "f6",
        "quick_action_2": "f7",
        "quick_action_3": "f8",
        "emergency_pause": "f9"
    }
    
    utils.cane_lib.safe_json_save(path, default_hotkeys)


def gaming_step():
    """Main gaming loop step"""
    if not gaming_enabled or not is_gaming_loop:
        return "CHAT"  # Fallback to normal chat
    
    try:
        # Gaming-specific logic here
        # For now, just return to normal chat
        time.sleep(0.1)
        return "CHAT"
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Gaming step error: {e}")
        return "CHAT"


def message_inputs(message: str):
    """Process AI message for gaming inputs"""
    if not gaming_enabled or not current_game:
        return
    
    try:
        # Check for gaming commands in AI message
        gaming_commands = extract_gaming_commands(message)
        
        for command in gaming_commands:
            execute_gaming_command(command)
        
        # Check for game state responses
        check_game_state_responses(message)
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Gaming message input error: {e}")


def extract_gaming_commands(message: str) -> List[str]:
    """Extract gaming commands from AI message"""
    commands = []
    
    if not current_game or current_game not in game_profiles:
        return commands
    
    game_profile = game_profiles[current_game]
    available_commands = game_profile.get("commands", {})
    
    message_lower = message.lower()
    
    # Look for command keywords
    for command_name, command_data in available_commands.items():
        command_keywords = [command_name.replace("_", " "), command_name]
        
        for keyword in command_keywords:
            if keyword.lower() in message_lower:
                commands.append(command_name)
                break
    
    return commands


def execute_gaming_command(command: str):
    """Execute a gaming command"""
    global last_gaming_action
    
    # Check cooldown
    current_time = time.time()
    if current_time - last_gaming_action < gaming_cooldown:
        return
    
    if not current_game or current_game not in game_profiles:
        return
    
    try:
        game_profile = game_profiles[current_game]
        commands = game_profile.get("commands", {})
        
        if command in commands:
            command_data = commands[command]
            key = command_data.get("key", "")
            
            if key:
                execute_key_action(key)
                last_gaming_action = current_time
                utils.zw_logging.update_debug_log(f"Executed gaming command: {command} ({key})")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Gaming command execution error: {e}")


def execute_key_action(key: str):
    """Execute keyboard/mouse action"""
    try:
        if key == "mouse_left":
            pyautogui.click()
        elif key == "mouse_right":
            pyautogui.rightClick()
        elif "+" in key:
            # Handle key combinations
            keys = key.split("+")
            pyautogui.hotkey(*keys)
        else:
            # Single key press
            pyautogui.press(key)
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Key action execution error: {e}")


def check_game_state_responses(message: str):
    """Check for game state-specific responses"""
    if not current_game or current_game not in game_profiles:
        return
    
    game_profile = game_profiles[current_game]
    responses = game_profile.get("responses", {})
    
    message_lower = message.lower()
    
    # Check for game state keywords
    for state, response_list in responses.items():
        state_keywords = {
            "death": ["died", "death", "killed", "game over"],
            "victory": ["won", "victory", "success", "completed"],
            "defeat": ["lost", "defeat", "failed"],
            "low_health": ["low health", "hurt", "damage", "injured"],
            "low_ammo": ["no ammo", "empty", "reload", "out of bullets"],
            "achievement": ["achievement", "unlocked", "completed", "milestone"]
        }
        
        keywords = state_keywords.get(state, [state])
        
        for keyword in keywords:
            if keyword in message_lower:
                utils.zw_logging.update_debug_log(f"Detected game state: {state}")
                break


def set_current_game(game_name: str) -> bool:
    """Set the current active game"""
    global current_game
    
    if game_name in game_profiles:
        current_game = game_name
        utils.zw_logging.update_debug_log(f"Set current game: {game_name}")
        return True
    else:
        utils.zw_logging.update_debug_log(f"Unknown game profile: {game_name}")
        return False


def enter_gaming_mode():
    """Enter gaming mode"""
    global is_gaming_loop
    
    if gaming_enabled:
        is_gaming_loop = True
        utils.settings.is_gaming_loop = True
        utils.zw_logging.update_debug_log("Entered gaming mode")


def exit_gaming_mode():
    """Exit gaming mode"""
    global is_gaming_loop
    
    is_gaming_loop = False
    utils.settings.is_gaming_loop = False
    utils.zw_logging.update_debug_log("Exited gaming mode")


def toggle_gaming_mode():
    """Toggle gaming mode on/off"""
    if is_gaming_loop:
        exit_gaming_mode()
    else:
        enter_gaming_mode()
    
    return is_gaming_loop


def get_gaming_status():
    """Get gaming system status"""
    return {
        "enabled": gaming_enabled,
        "gaming_mode": is_gaming_loop,
        "current_game": current_game,
        "available_games": list(game_profiles.keys()),
        "last_action_time": last_gaming_action
    }


def add_game_profile(game_name: str, profile_data: Dict[str, Any]) -> bool:
    """Add a new game profile"""
    global game_profiles
    
    try:
        game_profiles[game_name] = profile_data
        save_game_profiles()
        utils.zw_logging.update_debug_log(f"Added game profile: {game_name}")
        return True
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error adding game profile: {e}")
        return False


def save_game_profiles():
    """Save game profiles to file"""
    try:
        profiles_path = "Configurables/Gaming/game_profiles.json"
        utils.cane_lib.safe_json_save(profiles_path, game_profiles)
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error saving game profiles: {e}")


def get_available_commands() -> List[str]:
    """Get available commands for current game"""
    if not current_game or current_game not in game_profiles:
        return []
    
    game_profile = game_profiles[current_game]
    commands = game_profile.get("commands", {})
    
    return list(commands.keys())


# Initialize if enabled
if utils.settings.gaming_enabled:
    initialize()
