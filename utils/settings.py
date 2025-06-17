import os
import json
import utils.zw_logging

# Settings variables - loaded from .env and config files
vtube_enabled = False
web_ui_enabled = True
minecraft_enabled = False
discord_enabled = False
gaming_enabled = False

# Audio settings
autochat_enabled = True
autochat_mininum_chat_frames = 30
silero_vad_enabled = True
chunk_audio = True
max_chunk_count = 14

# Speech settings
stream_chats = True
speak_shadowchats = False
only_speak_when_spoken_to = False
remove_asterisks = True

# Memory settings
rag_enabled = True
lorebook_enabled = True
token_limit = 4096
max_tokens = 300

# UI settings
web_ui_port = 5000
primary_color = "blue"

# Advanced settings
rp_suppression = True
newline_cut = True
temperature = 0.7
top_p = 0.9

# Gaming and loop settings
is_gaming_loop = False
semi_auto_chat = False

# Debug settings
debug_logging = True

def load_settings():
    """Load settings from environment variables and config files"""
    global vtube_enabled, web_ui_enabled, minecraft_enabled, discord_enabled
    global gaming_enabled, autochat_enabled, autochat_mininum_chat_frames
    global silero_vad_enabled, chunk_audio, max_chunk_count, stream_chats
    global speak_shadowchats, only_speak_when_spoken_to, remove_asterisks
    global rag_enabled, lorebook_enabled, token_limit, max_tokens
    global web_ui_port, primary_color, rp_suppression, newline_cut
    global temperature, top_p, debug_logging
    
    # Load from environment variables
    vtube_enabled = os.getenv("VTUBE_ENABLED", "true").lower() == "true"
    web_ui_enabled = os.getenv("WEB_UI_ENABLED", "true").lower() == "true"
    minecraft_enabled = os.getenv("MINECRAFT_ENABLED", "false").lower() == "true"
    discord_enabled = os.getenv("DISCORD_ENABLED", "false").lower() == "true"
    gaming_enabled = os.getenv("GAMING_ENABLED", "false").lower() == "true"
    
    # Audio settings
    autochat_enabled = os.getenv("AUTOCHAT_ENABLED", "true").lower() == "true"
    autochat_mininum_chat_frames = int(os.getenv("AUTOCHAT_MINIMUM_CHAT_FRAMES", "30"))
    silero_vad_enabled = os.getenv("SILERO_VAD_ENABLED", "true").lower() == "true"
    chunk_audio = os.getenv("CHUNK_AUDIO", "true").lower() == "true"
    max_chunk_count = int(os.getenv("MAX_CHUNK_COUNT", "14"))
    
    # Speech settings
    stream_chats = os.getenv("STREAM_CHATS", "true").lower() == "true"
    speak_shadowchats = os.getenv("SPEAK_SHADOWCHATS", "false").lower() == "true"
    only_speak_when_spoken_to = os.getenv("ONLY_SPEAK_WHEN_SPOKEN_TO", "false").lower() == "true"
    remove_asterisks = True  # Always remove asterisks
    
    # Memory settings
    rag_enabled = os.getenv("RAG_ENABLED", "true").lower() == "true"
    lorebook_enabled = os.getenv("LOREBOOK_ENABLED", "true").lower() == "true"
    token_limit = int(os.getenv("TOKEN_LIMIT", "4096"))
    max_tokens = int(os.getenv("MAX_TOKENS", "300"))
    
    # UI settings
    web_ui_port = int(os.getenv("WEB_UI_PORT", "5000"))
    primary_color = os.getenv("PRIMARY_COLOR", "blue")
    
    # Advanced settings
    rp_suppression = os.getenv("RP_SUPPRESSION", "true").lower() == "true"
    newline_cut = os.getenv("NEWLINE_CUT", "true").lower() == "true"
    temperature = float(os.getenv("TEMPERATURE", "0.7"))
    top_p = float(os.getenv("TOP_P", "0.9"))
    
    # Debug settings
    debug_logging = os.getenv("DEBUG_LOGGING", "true").lower() == "true"
    
    utils.zw_logging.update_debug_log("Settings loaded from environment")


def save_settings():
    """Save current settings to config file"""
    settings_data = {
        "vtube_enabled": vtube_enabled,
        "web_ui_enabled": web_ui_enabled,
        "minecraft_enabled": minecraft_enabled,
        "discord_enabled": discord_enabled,
        "gaming_enabled": gaming_enabled,
        "autochat_enabled": autochat_enabled,
        "stream_chats": stream_chats,
        "speak_shadowchats": speak_shadowchats,
        "rag_enabled": rag_enabled,
        "lorebook_enabled": lorebook_enabled,
        "rp_suppression": rp_suppression,
        "newline_cut": newline_cut,
        "primary_color": primary_color
    }
    
    try:
        os.makedirs("Configurables/Settings", exist_ok=True)
        with open("Configurables/Settings/settings.json", 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, ensure_ascii=False, indent=2)
        utils.zw_logging.update_debug_log("Settings saved to file")
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error saving settings: {e}")


def get_setting(setting_name: str, default_value=None):
    """Get a specific setting value"""
    return globals().get(setting_name, default_value)


def set_setting(setting_name: str, value):
    """Set a specific setting value"""
    if setting_name in globals():
        globals()[setting_name] = value
        utils.zw_logging.update_debug_log(f"Setting updated: {setting_name} = {value}")
        return True
    return False


def toggle_setting(setting_name: str):
    """Toggle a boolean setting"""
    if setting_name in globals() and isinstance(globals()[setting_name], bool):
        globals()[setting_name] = not globals()[setting_name]
        utils.zw_logging.update_debug_log(f"Setting toggled: {setting_name} = {globals()[setting_name]}")
        return globals()[setting_name]
    return None


# Load settings on import
load_settings()
