"""
Tag Task Controller - Manages contextual tags and task assignments
Provides dynamic behavior modification based on conversation context
"""

import os
import json
import re
import time
import threading
from typing import List, Dict, Any, Optional, Set
import utils.zw_logging
import utils.cane_lib
import API.task_profiles

# Tag system variables
active_tags = set()
tag_history = []
tag_rules = {}
automatic_tagging = True
tag_decay_time = 3600  # 1 hour
max_active_tags = 10

def initialize():
    """Initialize tag task controller"""
    global automatic_tagging
    
    automatic_tagging = os.getenv("AUTO_TAGGING_ENABLED", "true").lower() == "true"
    
    load_tag_rules()
    load_tag_history()
    
    # Start tag decay thread
    decay_thread = threading.Thread(target=tag_decay_loop)
    decay_thread.daemon = True
    decay_thread.start()
    
    utils.zw_logging.update_debug_log("Tag task controller initialized")


def tag_decay_loop():
    """Background loop to decay old tags"""
    while True:
        try:
            decay_old_tags()
            time.sleep(300)  # Check every 5 minutes
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Tag decay loop error: {e}")
            time.sleep(600)


def load_tag_rules():
    """Load tag detection rules"""
    global tag_rules
    
    rules_path = "Configurables/Tags/tag_rules.json"
    
    try:
        if os.path.exists(rules_path):
            tag_rules = utils.cane_lib.safe_json_load(rules_path, {})
        else:
            create_default_tag_rules(rules_path)
            tag_rules = utils.cane_lib.safe_json_load(rules_path, {})
        
        utils.zw_logging.update_debug_log(f"Loaded {len(tag_rules)} tag rules")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error loading tag rules: {e}")
        tag_rules = {}


def create_default_tag_rules(path: str):
    """Create default tag detection rules"""
    utils.cane_lib.ensure_directory(os.path.dirname(path))
    
    default_rules = {
        "gaming": {
            "keywords": ["game", "gaming", "play", "player", "level", "boss", "quest", "rpg", "fps", "mmorpg"],
            "patterns": [r"\bgam(e|ing)\b", r"\bplay(ing|ed)?\b"],
            "weight": 1.0,
            "task_profile": "gaming",
            "description": "Gaming and video game related content"
        },
        "creative": {
            "keywords": ["art", "creative", "draw", "paint", "music", "write", "story", "poem", "design"],
            "patterns": [r"\bcreate?\b", r"\bart\b", r"\bdraw\b"],
            "weight": 1.0,
            "task_profile": "creative",
            "description": "Creative and artistic activities"
        },
        "learning": {
            "keywords": ["learn", "study", "education", "teach", "explain", "understand", "knowledge"],
            "patterns": [r"\blearn(ing)?\b", r"\bstud(y|ying)\b", r"\bteach\b"],
            "weight": 1.0,
            "task_profile": "study_buddy",
            "description": "Learning and educational content"
        },
        "technical": {
            "keywords": ["code", "programming", "software", "computer", "technology", "ai", "algorithm"],
            "patterns": [r"\bcode?\b", r"\bprogram(ming)?\b", r"\btech\b"],
            "weight": 1.0,
            "task_profile": "technical",
            "description": "Technical and programming content"
        },
        "casual": {
            "keywords": ["chat", "talk", "conversation", "hello", "hi", "how are you"],
            "patterns": [r"\bhello\b", r"\bhi\b", r"\bchat\b"],
            "weight": 0.8,
            "task_profile": "casual_chat",
            "description": "Casual conversation"
        },
        "help": {
            "keywords": ["help", "assist", "support", "question", "problem", "issue"],
            "patterns": [r"\bhelp\b", r"\bquestion\b", r"\bproblem\b"],
            "weight": 1.2,
            "task_profile": "helpful",
            "description": "Help and assistance requests"
        },
        "emotional": {
            "keywords": ["sad", "happy", "angry", "excited", "worried", "stressed", "anxious"],
            "patterns": [r"\bfeel(ing)?\b", r"\bemot(ion|ional)\b"],
            "weight": 1.5,
            "task_profile": "supportive",
            "description": "Emotional content and support"
        }
    }
    
    utils.cane_lib.safe_json_save(path, default_rules)
    utils.zw_logging.update_debug_log(f"Created default tag rules: {path}")


def analyze_message_for_tags(message: str) -> Set[str]:
    """Analyze message and return detected tags"""
    if not message or not automatic_tagging:
        return set()
    
    detected_tags = set()
    message_lower = message.lower()
    
    for tag_name, rule in tag_rules.items():
        confidence = 0.0
        
        # Check keywords
        keywords = rule.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in message_lower:
                confidence += 0.3
        
        # Check patterns
        patterns = rule.get("patterns", [])
        for pattern in patterns:
            if re.search(pattern, message_lower):
                confidence += 0.4
        
        # Apply weight
        weight = rule.get("weight", 1.0)
        confidence *= weight
        
        # Add tag if confidence is high enough
        if confidence >= 0.5:
            detected_tags.add(tag_name)
    
    return detected_tags


def add_tags(tags: Set[str], source: str = "auto"):
    """Add tags to active set"""
    global active_tags, tag_history
    
    if not tags:
        return
    
    current_time = time.time()
    
    for tag in tags:
        if tag not in active_tags:
            active_tags.add(tag)
            
            # Add to history
            tag_history.append({
                "tag": tag,
                "action": "added",
                "source": source,
                "timestamp": current_time
            })
            
            # Check for task profile association
            if tag in tag_rules:
                task_profile = tag_rules[tag].get("task_profile")
                if task_profile:
                    API.task_profiles.set_current_task(task_profile)
            
            utils.zw_logging.update_debug_log(f"Added tag: {tag} (source: {source})")
    
    # Limit active tags
    if len(active_tags) > max_active_tags:
        # Remove oldest tags
        oldest_tags = sorted(tag_history, key=lambda x: x["timestamp"])
        for old_tag_entry in oldest_tags:
            if old_tag_entry["tag"] in active_tags:
                active_tags.remove(old_tag_entry["tag"])
                break


def remove_tags(tags: Set[str], source: str = "manual"):
    """Remove tags from active set"""
    global active_tags, tag_history
    
    current_time = time.time()
    
    for tag in tags:
        if tag in active_tags:
            active_tags.remove(tag)
            
            # Add to history
            tag_history.append({
                "tag": tag,
                "action": "removed",
                "source": source,
                "timestamp": current_time
            })
            
            utils.zw_logging.update_debug_log(f"Removed tag: {tag} (source: {source})")


def decay_old_tags():
    """Remove old tags based on decay time"""
    if not active_tags:
        return
    
    current_time = time.time()
    tags_to_remove = set()
    
    # Find tags that should decay
    for tag_entry in reversed(tag_history):
        if tag_entry["action"] == "added" and tag_entry["tag"] in active_tags:
            if current_time - tag_entry["timestamp"] > tag_decay_time:
                tags_to_remove.add(tag_entry["tag"])
    
    if tags_to_remove:
        remove_tags(tags_to_remove, "decay")
        utils.zw_logging.update_debug_log(f"Decayed {len(tags_to_remove)} old tags")


def process_message_tags(message: str):
    """Process message for automatic tagging"""
    if not automatic_tagging:
        return
    
    try:
        detected_tags = analyze_message_for_tags(message)
        
        if detected_tags:
            add_tags(detected_tags, "auto")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Tag processing error: {e}")


def get_active_tags() -> Set[str]:
    """Get currently active tags"""
    return active_tags.copy()


def get_tag_context() -> str:
    """Get context string based on active tags"""
    if not active_tags:
        return ""
    
    context_parts = ["Current context tags:"]
    
    for tag in active_tags:
        if tag in tag_rules:
            description = tag_rules[tag].get("description", tag)
            context_parts.append(f"- {tag}: {description}")
        else:
            context_parts.append(f"- {tag}")
    
    return "\n".join(context_parts)


def get_recommended_task() -> Optional[str]:
    """Get recommended task based on active tags"""
    if not active_tags:
        return None
    
    # Score tasks based on active tags
    task_scores = {}
    
    for tag in active_tags:
        if tag in tag_rules:
            task_profile = tag_rules[tag].get("task_profile")
            if task_profile:
                weight = tag_rules[tag].get("weight", 1.0)
                task_scores[task_profile] = task_scores.get(task_profile, 0) + weight
    
    if task_scores:
        # Return highest scoring task
        best_task = max(task_scores.items(), key=lambda x: x[1])
        return best_task[0]
    
    return None


def manual_add_tag(tag: str) -> bool:
    """Manually add a tag"""
    try:
        add_tags({tag}, "manual")
        return True
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Manual tag add error: {e}")
        return False


def manual_remove_tag(tag: str) -> bool:
    """Manually remove a tag"""
    try:
        remove_tags({tag}, "manual")
        return True
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Manual tag remove error: {e}")
        return False


def clear_all_tags():
    """Clear all active tags"""
    global active_tags
    
    tags_to_remove = active_tags.copy()
    remove_tags(tags_to_remove, "clear")


def load_tag_history():
    """Load tag history from file"""
    global tag_history
    
    try:
        history_path = "Configurables/Tags/tag_history.json"
        tag_history = utils.cane_lib.safe_json_load(history_path, [])
        
        # Rebuild active tags from recent history
        rebuild_active_tags_from_history()
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error loading tag history: {e}")
        tag_history = []


def save_tag_history():
    """Save tag history to file"""
    try:
        history_path = "Configurables/Tags/tag_history.json"
        utils.cane_lib.ensure_directory(os.path.dirname(history_path))
        
        # Keep only recent history (last 500 entries)
        recent_history = tag_history[-500:] if len(tag_history) > 500 else tag_history
        
        utils.cane_lib.safe_json_save(history_path, recent_history)
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error saving tag history: {e}")


def rebuild_active_tags_from_history():
    """Rebuild active tags from history"""
    global active_tags
    
    active_tags = set()
    current_time = time.time()
    
    # Process history to find currently active tags
    tag_states = {}
    
    for entry in tag_history:
        tag = entry["tag"]
        action = entry["action"]
        timestamp = entry["timestamp"]
        
        # Skip very old entries
        if current_time - timestamp > tag_decay_time:
            continue
        
        if action == "added":
            tag_states[tag] = timestamp
        elif action == "removed":
            if tag in tag_states:
                del tag_states[tag]
    
    active_tags = set(tag_states.keys())


def get_tag_statistics():
    """Get tag system statistics"""
    return {
        "active_tags": len(active_tags),
        "total_rules": len(tag_rules),
        "history_entries": len(tag_history),
        "automatic_tagging": automatic_tagging,
        "decay_time_hours": tag_decay_time / 3600
    }


# Initialize on import
initialize()
