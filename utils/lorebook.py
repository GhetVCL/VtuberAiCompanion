"""
Lorebook System - Manages character knowledge and world information
Provides contextual information injection based on conversation topics
"""

import os
import json
import re
import threading
from typing import List, Dict, Any, Optional
import utils.zw_logging
import utils.cane_lib

# Lorebook variables
lorebook_entries = []
active_entries = []
lorebook_enabled = True
max_active_entries = 5
relevance_threshold = 0.3

def initialize():
    """Initialize the lorebook system"""
    global lorebook_enabled
    
    lorebook_enabled = os.getenv("LOREBOOK_ENABLED", "true").lower() == "true"
    
    if lorebook_enabled:
        load_lorebook()
    
    utils.zw_logging.update_debug_log("Lorebook system initialized")


def load_lorebook():
    """Load lorebook entries from files"""
    global lorebook_entries
    
    lorebook_dir = "Configurables/Lorebook"
    utils.cane_lib.ensure_directory(lorebook_dir)
    
    lorebook_entries = []
    
    try:
        # Load main lorebook file
        main_lorebook_path = os.path.join(lorebook_dir, "lorebook.json")
        
        if os.path.exists(main_lorebook_path):
            with open(main_lorebook_path, 'r', encoding='utf-8') as f:
                lorebook_data = json.load(f)
                lorebook_entries = lorebook_data.get("entries", [])
        else:
            create_default_lorebook(main_lorebook_path)
            load_lorebook()  # Reload after creating default
        
        # Load additional lorebook files
        for filename in os.listdir(lorebook_dir):
            if filename.endswith('.json') and filename != 'lorebook.json':
                try:
                    file_path = os.path.join(lorebook_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        additional_data = json.load(f)
                        additional_entries = additional_data.get("entries", [])
                        lorebook_entries.extend(additional_entries)
                except Exception as e:
                    utils.zw_logging.update_debug_log(f"Error loading lorebook file {filename}: {e}")
        
        utils.zw_logging.update_debug_log(f"Loaded {len(lorebook_entries)} lorebook entries")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error loading lorebook: {e}")
        lorebook_entries = []


def create_default_lorebook(path: str):
    """Create default lorebook entries"""
    default_lorebook = {
        "metadata": {
            "name": "Default Lorebook",
            "description": "Default knowledge base for the AI character",
            "version": "1.0"
        },
        "entries": [
            {
                "id": "personality_core",
                "title": "Core Personality",
                "content": "You are a friendly AI VTuber who enjoys chatting with viewers. You're enthusiastic, helpful, and have a warm personality.",
                "keywords": ["personality", "character", "who are you", "what are you"],
                "priority": 10,
                "enabled": True
            },
            {
                "id": "streaming_setup",
                "title": "Streaming Knowledge",
                "content": "You understand streaming, VTubing, and online content creation. You can discuss games, technology, and entertainment topics.",
                "keywords": ["stream", "streaming", "vtube", "vtuber", "games", "gaming"],
                "priority": 8,
                "enabled": True
            },
            {
                "id": "ai_knowledge",
                "title": "AI Understanding",
                "content": "You are powered by Gemini and features speech recognition, natural language processing, and text-to-speech synthesis.",
                "keywords": ["ai", "artificial intelligence", "technology", "how do you work"],
                "priority": 7,
                "enabled": True
            },
            {
                "id": "helpful_assistant",
                "title": "Helpful Nature",
                "content": "You enjoy helping users with questions, providing information, and engaging in meaningful conversations about various topics.",
                "keywords": ["help", "question", "information", "assist", "explain"],
                "priority": 6,
                "enabled": True
            }
        ]
    }
    
    utils.cane_lib.safe_json_save(path, default_lorebook)
    utils.zw_logging.update_debug_log(f"Created default lorebook: {path}")


def get_relevant_entries(message: str, max_entries: int = None) -> List[Dict[str, Any]]:
    """Get lorebook entries relevant to the current message"""
    if not lorebook_enabled or not lorebook_entries:
        return []
    
    if max_entries is None:
        max_entries = max_active_entries
    
    relevant_entries = []
    message_lower = message.lower()
    
    for entry in lorebook_entries:
        if not entry.get("enabled", True):
            continue
        
        relevance_score = calculate_relevance(entry, message_lower)
        
        if relevance_score >= relevance_threshold:
            entry_copy = entry.copy()
            entry_copy["relevance_score"] = relevance_score
            relevant_entries.append(entry_copy)
    
    # Sort by priority and relevance
    relevant_entries.sort(key=lambda x: (x.get("priority", 0), x["relevance_score"]), reverse=True)
    
    return relevant_entries[:max_entries]


def calculate_relevance(entry: Dict[str, Any], message: str) -> float:
    """Calculate relevance score for a lorebook entry"""
    keywords = entry.get("keywords", [])
    if not keywords:
        return 0.0
    
    matches = 0
    total_keywords = len(keywords)
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        
        # Check for exact word matches
        if re.search(r'\b' + re.escape(keyword_lower) + r'\b', message):
            matches += 1
        # Check for partial matches
        elif keyword_lower in message:
            matches += 0.5
    
    # Calculate base relevance score
    relevance = matches / total_keywords if total_keywords > 0 else 0.0
    
    # Boost score for high priority entries
    priority_boost = min(entry.get("priority", 0) / 10.0, 0.3)
    relevance += priority_boost
    
    return min(relevance, 1.0)


def get_lorebook_context(message: str) -> str:
    """Get formatted lorebook context for the current message"""
    relevant_entries = get_relevant_entries(message)
    
    if not relevant_entries:
        return ""
    
    context_parts = []
    context_parts.append("Relevant knowledge:")
    
    for entry in relevant_entries:
        title = entry.get("title", "Knowledge Entry")
        content = entry.get("content", "")
        
        if content:
            context_parts.append(f"- {title}: {content}")
    
    return "\n".join(context_parts)


def add_lorebook_entry(title: str, content: str, keywords: List[str], priority: int = 5) -> bool:
    """Add a new lorebook entry"""
    global lorebook_entries
    
    try:
        new_entry = {
            "id": f"entry_{len(lorebook_entries) + 1}_{int(time.time())}",
            "title": title,
            "content": content,
            "keywords": keywords,
            "priority": priority,
            "enabled": True,
            "created": time.time()
        }
        
        lorebook_entries.append(new_entry)
        save_lorebook()
        
        utils.zw_logging.update_debug_log(f"Added lorebook entry: {title}")
        return True
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error adding lorebook entry: {e}")
        return False


def remove_lorebook_entry(entry_id: str) -> bool:
    """Remove a lorebook entry by ID"""
    global lorebook_entries
    
    try:
        lorebook_entries = [entry for entry in lorebook_entries if entry.get("id") != entry_id]
        save_lorebook()
        
        utils.zw_logging.update_debug_log(f"Removed lorebook entry: {entry_id}")
        return True
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error removing lorebook entry: {e}")
        return False


def update_lorebook_entry(entry_id: str, updates: Dict[str, Any]) -> bool:
    """Update a lorebook entry"""
    try:
        for entry in lorebook_entries:
            if entry.get("id") == entry_id:
                entry.update(updates)
                save_lorebook()
                utils.zw_logging.update_debug_log(f"Updated lorebook entry: {entry_id}")
                return True
        
        return False
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error updating lorebook entry: {e}")
        return False


def save_lorebook():
    """Save lorebook entries to file"""
    try:
        lorebook_data = {
            "metadata": {
                "name": "AI Character Lorebook",
                "description": "Knowledge base for the AI character",
                "version": "1.0",
                "last_updated": time.time()
            },
            "entries": lorebook_entries
        }
        
        lorebook_path = "Configurables/Lorebook/lorebook.json"
        utils.cane_lib.safe_json_save(lorebook_path, lorebook_data)
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error saving lorebook: {e}")


def search_lorebook(query: str) -> List[Dict[str, Any]]:
    """Search lorebook entries"""
    if not query:
        return []
    
    query_lower = query.lower()
    results = []
    
    for entry in lorebook_entries:
        if not entry.get("enabled", True):
            continue
        
        # Search in title, content, and keywords
        title = entry.get("title", "").lower()
        content = entry.get("content", "").lower()
        keywords = [kw.lower() for kw in entry.get("keywords", [])]
        
        if (query_lower in title or 
            query_lower in content or 
            any(query_lower in kw for kw in keywords)):
            results.append(entry)
    
    return results


def get_lorebook_stats():
    """Get lorebook statistics"""
    enabled_entries = [entry for entry in lorebook_entries if entry.get("enabled", True)]
    
    return {
        "total_entries": len(lorebook_entries),
        "enabled_entries": len(enabled_entries),
        "disabled_entries": len(lorebook_entries) - len(enabled_entries),
        "lorebook_enabled": lorebook_enabled
    }


def toggle_lorebook(enabled: bool = None):
    """Toggle lorebook system on/off"""
    global lorebook_enabled
    
    if enabled is None:
        lorebook_enabled = not lorebook_enabled
    else:
        lorebook_enabled = enabled
    
    utils.zw_logging.update_debug_log(f"Lorebook {'enabled' if lorebook_enabled else 'disabled'}")
    return lorebook_enabled


# Initialize on import
initialize()
