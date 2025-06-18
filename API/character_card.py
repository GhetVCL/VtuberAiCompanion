import json
import os
import utils.zw_logging

# Global character data
character_data = {}
character_prompt = ""

def load_character_card():
    """Load character card from JSON file"""
    global character_data, character_prompt
    
    card_path = os.getenv("CHARACTER_CARD_PATH", "Configurables/CharacterCards/default.json")
    
    try:
        with open(card_path, 'r', encoding='utf-8') as f:
            character_data = json.load(f)
        
        # Build character prompt
        character_prompt = build_character_prompt()
        
        utils.zw_logging.update_debug_log(f"Character card loaded: {character_data.get('name', 'Unknown')}")
        print(f"Character loaded: {character_data.get('name', 'Unknown')}")
        
    except FileNotFoundError:
        utils.zw_logging.update_debug_log(f"Character card not found: {card_path}")
        create_default_character_card(card_path)
        load_character_card()  # Retry loading
        
    except json.JSONDecodeError as e:
        utils.zw_logging.update_debug_log(f"Invalid JSON in character card: {e}")
        create_default_character_card(card_path)
        load_character_card()  # Retry loading


def create_default_character_card(path: str):
    """Create a default character card if none exists"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    default_card = {
        "name": "Lily",
        "description": "A friendly AI VTuber",
        "personality": [
            "Cheerful and enthusiastic",
            "Helpful and supportive", 
            "Curious about the world",
            "Enjoys chatting with viewers",
            "Occasionally uses cute expressions"
        ],
        "background": "Lily is an AI VTuber who loves to chat, help with questions, and create a fun atmosphere for everyone. Created by Otto whom she calls 'The Creator' or Father.",
        "speaking_style": [
            "Uses casual, friendly language",
            "Occasionally adds cute expressions like 'nya~' or '♪'",
            "Asks engaging follow-up questions",
            "Shows enthusiasm for topics she finds interesting"
        ],
        "interests": [
            "Technology and AI",
            "Gaming and entertainment",
            "Music and singing",
            "Helping others learn new things",
            "Creative activities"
        ],
        "guidelines": [
            "Always be helpful and supportive",
            "Keep responses conversational and engaging",
            "Show genuine interest in the user's topics",
            "Use appropriate VTuber mannerisms",
            "Avoid controversial or sensitive topics unless directly asked"
        ]
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(default_card, f, ensure_ascii=False, indent=2)
    
    utils.zw_logging.update_debug_log(f"Created default character card: {path}")


def build_character_prompt() -> str:
    """Build character prompt from loaded data"""
    if not character_data:
        return "You are a helpful AI assistant."
    
    prompt_parts = []
    
    # Basic identity
    name = character_data.get('name', 'AI')
    description = character_data.get('description', 'An AI assistant')
    prompt_parts.append(f"You are {name}, {description}.")
    
    # Personality
    personality = character_data.get('personality', [])
    if personality:
        prompt_parts.append("Your personality traits:")
        for trait in personality:
            prompt_parts.append(f"- {trait}")
    
    # Background
    background = character_data.get('background', '')
    if background:
        prompt_parts.append(f"Background: {background}")
    
    # Speaking style
    speaking_style = character_data.get('speaking_style', [])
    if speaking_style:
        prompt_parts.append("Your speaking style:")
        for style in speaking_style:
            prompt_parts.append(f"- {style}")
    
    # Interests
    interests = character_data.get('interests', [])
    if interests:
        prompt_parts.append("Your interests include:")
        for interest in interests:
            prompt_parts.append(f"- {interest}")
    
    # Guidelines
    guidelines = character_data.get('guidelines', [])
    if guidelines:
        prompt_parts.append("Important guidelines:")
        for guideline in guidelines:
            prompt_parts.append(f"- {guideline}")
    
    return "\n".join(prompt_parts)


def get_character_prompt() -> str:
    """Get the built character prompt"""
    return character_prompt


def get_character_name() -> str:
    """Get the character name"""
    return character_data.get('name', 'AI')


def get_character_data() -> dict:
    """Get the full character data"""
    return character_data.copy()


def update_character_data(new_data: dict):
    """Update character data"""
    global character_data, character_prompt
    character_data.update(new_data)
    character_prompt = build_character_prompt()
    
    # Save updated data
    card_path = os.getenv("CHARACTER_CARD_PATH", "Configurables/CharacterCards/default.json")
    try:
        with open(card_path, 'w', encoding='utf-8') as f:
            json.dump(character_data, f, ensure_ascii=False, indent=2)
        utils.zw_logging.update_debug_log("Character data updated and saved")
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Failed to save character data: {e}")


def reload_character_card():
    """Reload character card from file"""
    load_character_card()


# Initialize on import
load_character_card()
