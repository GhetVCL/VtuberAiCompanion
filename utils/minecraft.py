import re
import utils.zw_logging
import utils.settings

# Minecraft integration variables
minecraft_enabled = False
minecraft_commands = []
last_command_result = ""

def initialize():
    """Initialize Minecraft integration"""
    global minecraft_enabled
    minecraft_enabled = utils.settings.minecraft_enabled
    
    if minecraft_enabled:
        load_minecraft_commands()
        utils.zw_logging.update_debug_log("Minecraft integration initialized")


def load_minecraft_commands():
    """Load available Minecraft commands"""
    global minecraft_commands
    
    # Basic Minecraft commands that the AI can use
    minecraft_commands = [
        "look",
        "move",
        "jump",
        "dig",
        "place",
        "craft",
        "inventory",
        "chat",
        "follow",
        "goto",
        "mine",
        "build"
    ]
    
    utils.zw_logging.update_debug_log(f"Loaded {len(minecraft_commands)} Minecraft commands")


def check_for_command(message: str):
    """Check AI message for Minecraft commands"""
    if not minecraft_enabled:
        return
    
    try:
        # Look for command patterns in the AI's message
        command_patterns = [
            r"/mc\s+(\w+)(?:\s+(.+))?/",  # /mc command args/
            r"/minecraft\s+(\w+)(?:\s+(.+))?/",  # /minecraft command args/
            r"\[minecraft\]\s*(\w+)(?:\s+(.+))?",  # [minecraft] command args
        ]
        
        for pattern in command_patterns:
            matches = re.findall(pattern, message.lower())
            for match in matches:
                command = match[0] if match[0] else ""
                args = match[1] if len(match) > 1 and match[1] else ""
                
                if command in minecraft_commands:
                    execute_minecraft_command(command, args)
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Minecraft command check error: {e}")


def execute_minecraft_command(command: str, args: str = ""):
    """Execute a Minecraft command"""
    global last_command_result
    
    try:
        full_command = f"{command} {args}".strip()
        utils.zw_logging.update_debug_log(f"Executing Minecraft command: {full_command}")
        
        # This is a placeholder for actual Minecraft integration
        # Real implementation would use Baritone, Wurst, or other command mods
        
        command_results = {
            "look": "Looking around the area",
            "move": f"Moving {args if args else 'forward'}",
            "jump": "Jumping",
            "dig": f"Digging {args if args else 'block in front'}",
            "place": f"Placing {args if args else 'block'}",
            "craft": f"Crafting {args if args else 'item'}",
            "inventory": "Checking inventory",
            "chat": f"Chatting: {args}",
            "follow": f"Following {args if args else 'player'}",
            "goto": f"Going to {args if args else 'location'}",
            "mine": f"Mining {args if args else 'resources'}",
            "build": f"Building {args if args else 'structure'}"
        }
        
        result = command_results.get(command, f"Unknown command: {command}")
        last_command_result = result
        
        utils.zw_logging.update_debug_log(f"Minecraft command result: {result}")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Minecraft command execution error: {e}")
        last_command_result = f"Error executing command: {e}"


def minecraft_chat():
    """Handle Minecraft chat functionality"""
    if not minecraft_enabled:
        return
    
    try:
        # This would send the AI's response to Minecraft chat
        utils.zw_logging.update_debug_log("Sending message to Minecraft chat")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Minecraft chat error: {e}")


def get_minecraft_status():
    """Get Minecraft integration status"""
    return {
        "enabled": minecraft_enabled,
        "available_commands": minecraft_commands,
        "last_command_result": last_command_result
    }


def enable_minecraft():
    """Enable Minecraft integration"""
    global minecraft_enabled
    minecraft_enabled = True
    utils.settings.set_setting("minecraft_enabled", True)
    initialize()


def disable_minecraft():
    """Disable Minecraft integration"""
    global minecraft_enabled
    minecraft_enabled = False
    utils.settings.set_setting("minecraft_enabled", False)


# Initialize if enabled
if utils.settings.minecraft_enabled:
    initialize()
