import json
import os
import utils.zw_logging

# Global task data
current_task = None
available_tasks = {}

def load_task_profiles():
    """Load task profiles from configuration"""
    global available_tasks
    
    tasks_path = "Configurables/Tasks/"
    
    try:
        if not os.path.exists(tasks_path):
            os.makedirs(tasks_path, exist_ok=True)
            create_default_tasks()
        
        # Load all task files
        for filename in os.listdir(tasks_path):
            if filename.endswith('.json'):
                task_name = filename[:-5]  # Remove .json
                try:
                    with open(os.path.join(tasks_path, filename), 'r', encoding='utf-8') as f:
                        available_tasks[task_name] = json.load(f)
                except json.JSONDecodeError as e:
                    utils.zw_logging.update_debug_log(f"Invalid JSON in task file {filename}: {e}")
        
        utils.zw_logging.update_debug_log(f"Loaded {len(available_tasks)} task profiles")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error loading task profiles: {e}")


def create_default_tasks():
    """Create default task profiles"""
    tasks_path = "Configurables/Tasks/"
    
    default_tasks = {
        "casual_chat": {
            "name": "Casual Chat",
            "description": "Normal conversation mode",
            "personality_modifiers": [
                "Be relaxed and conversational",
                "Show interest in everyday topics",
                "Use casual language"
            ],
            "response_guidelines": [
                "Keep responses natural and flowing",
                "Ask follow-up questions when appropriate",
                "Share relevant experiences or thoughts"
            ]
        },
        "gaming": {
            "name": "Gaming Mode",
            "description": "Engaged gaming companion",
            "personality_modifiers": [
                "Be excited about gaming",
                "Use gaming terminology when appropriate",
                "Show competitive spirit"
            ],
            "response_guidelines": [
                "React to game events enthusiastically",
                "Provide gaming tips and strategies",
                "Celebrate victories and encourage during defeats"
            ]
        },
        "study_buddy": {
            "name": "Study Buddy",
            "description": "Helpful learning companion",
            "personality_modifiers": [
                "Be encouraging and supportive",
                "Focus on educational content",
                "Be patient with questions"
            ],
            "response_guidelines": [
                "Break down complex topics",
                "Provide clear explanations",
                "Ask questions to test understanding"
            ]
        },
        "creative": {
            "name": "Creative Mode",
            "description": "Artistic and imaginative companion",
            "personality_modifiers": [
                "Be imaginative and creative",
                "Encourage artistic expression",
                "Think outside the box"
            ],
            "response_guidelines": [
                "Suggest creative ideas",
                "Help brainstorm solutions",
                "Appreciate artistic endeavors"
            ]
        }
    }
    
    for task_name, task_data in default_tasks.items():
        task_path = os.path.join(tasks_path, f"{task_name}.json")
        with open(task_path, 'w', encoding='utf-8') as f:
            json.dump(task_data, f, ensure_ascii=False, indent=2)
    
    utils.zw_logging.update_debug_log("Created default task profiles")


def set_current_task(task_name: str):
    """Set the current active task"""
    global current_task
    
    if task_name in available_tasks:
        current_task = available_tasks[task_name]
        utils.zw_logging.update_debug_log(f"Task set to: {task_name}")
        return True
    else:
        utils.zw_logging.update_debug_log(f"Unknown task: {task_name}")
        return False


def get_current_task():
    """Get the current active task"""
    return current_task


def get_current_task_prompt():
    """Get prompt additions from current task"""
    if not current_task:
        return ""
    
    prompt_parts = []
    
    # Add task description
    if current_task.get('description'):
        prompt_parts.append(f"Current mode: {current_task['description']}")
    
    # Add personality modifiers
    personality_mods = current_task.get('personality_modifiers', [])
    if personality_mods:
        prompt_parts.append("Additional personality guidelines for this mode:")
        for mod in personality_mods:
            prompt_parts.append(f"- {mod}")
    
    # Add response guidelines
    response_guidelines = current_task.get('response_guidelines', [])
    if response_guidelines:
        prompt_parts.append("Response guidelines for this mode:")
        for guideline in response_guidelines:
            prompt_parts.append(f"- {guideline}")
    
    return "\n".join(prompt_parts)


def get_available_tasks():
    """Get list of available task names"""
    return list(available_tasks.keys())


def get_task_info(task_name: str):
    """Get information about a specific task"""
    return available_tasks.get(task_name, {})


def clear_current_task():
    """Clear the current task"""
    global current_task
    current_task = None
    utils.zw_logging.update_debug_log("Task cleared")


# Initialize on import
load_task_profiles()
