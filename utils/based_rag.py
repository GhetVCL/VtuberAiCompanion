"""
Based RAG (Retrieval-Augmented Generation) System
Provides semantic search and retrieval of relevant conversation history
"""

import os
import json
import time
import threading
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import utils.zw_logging
import utils.cane_lib

# RAG system variables
rag_enabled = True
conversation_embeddings = []
conversation_index = []
max_rag_entries = 1000
similarity_threshold = 0.6
is_rag_initialized = False
rag_update_thread = None
is_updating = False

def initialize():
    """Initialize the RAG system"""
    global rag_enabled, is_rag_initialized, rag_update_thread
    
    rag_enabled = os.getenv("RAG_ENABLED", "true").lower() == "true"
    
    if not rag_enabled:
        utils.zw_logging.update_debug_log("RAG system disabled")
        return
    
    # Load existing RAG data
    load_rag_data()
    
    # Start background update thread
    rag_update_thread = threading.Thread(target=rag_update_loop)
    rag_update_thread.daemon = True
    rag_update_thread.start()
    
    is_rag_initialized = True
    utils.zw_logging.update_debug_log("RAG system initialized")


def rag_update_loop():
    """Background loop to update RAG embeddings"""
    global is_updating
    
    while rag_enabled:
        try:
            # Update RAG data every 10 minutes
            time.sleep(600)
            
            if not is_updating:
                update_rag_from_conversations()
            
        except Exception as e:
            utils.zw_logging.update_debug_log(f"RAG update loop error: {e}")
            time.sleep(300)


def simple_text_embedding(text: str) -> List[float]:
    """Create a simple text embedding using basic features"""
    if not text:
        return [0.0] * 50  # 50-dimensional embedding
    
    text_lower = text.lower()
    
    # Basic text features
    features = []
    
    # Length features
    features.append(min(len(text) / 100.0, 1.0))  # Normalized length
    features.append(min(len(text.split()) / 50.0, 1.0))  # Normalized word count
    
    # Character frequency features (a-z)
    char_counts = {chr(i): 0 for i in range(ord('a'), ord('z') + 1)}
    for char in text_lower:
        if char in char_counts:
            char_counts[char] += 1
    
    total_chars = max(sum(char_counts.values()), 1)
    for char in sorted(char_counts.keys()):
        features.append(char_counts[char] / total_chars)
    
    # Punctuation features
    punctuation_count = sum(1 for char in text if char in '.,!?;:')
    features.append(min(punctuation_count / max(len(text), 1), 1.0))
    
    # Question feature
    features.append(1.0 if '?' in text else 0.0)
    
    # Exclamation feature
    features.append(1.0 if '!' in text else 0.0)
    
    # Pad or truncate to exactly 50 dimensions
    while len(features) < 50:
        features.append(0.0)
    
    return features[:50]


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    if not vec1 or not vec2:
        return 0.0
    
    # Convert to numpy arrays
    a = np.array(vec1)
    b = np.array(vec2)
    
    # Calculate cosine similarity
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)


def add_conversation_to_rag(user_message: str, ai_response: str):
    """Add a conversation to the RAG system"""
    global conversation_embeddings, conversation_index
    
    if not rag_enabled or not user_message or not ai_response:
        return
    
    try:
        # Create embeddings for both messages
        user_embedding = simple_text_embedding(user_message)
        ai_embedding = simple_text_embedding(ai_response)
        
        # Create conversation entry
        conversation_entry = {
            "user_message": user_message,
            "ai_response": ai_response,
            "timestamp": time.time(),
            "date": datetime.now().isoformat(),
            "user_embedding": user_embedding,
            "ai_embedding": ai_embedding
        }
        
        conversation_index.append(conversation_entry)
        
        # Maintain size limit
        if len(conversation_index) > max_rag_entries:
            conversation_index = conversation_index[-max_rag_entries:]
        
        utils.zw_logging.update_debug_log("Added conversation to RAG system")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error adding conversation to RAG: {e}")


def search_similar_conversations(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search for similar conversations"""
    if not rag_enabled or not conversation_index or not query:
        return []
    
    try:
        query_embedding = simple_text_embedding(query)
        similarities = []
        
        for i, conv in enumerate(conversation_index):
            # Calculate similarity with user message
            user_sim = cosine_similarity(query_embedding, conv["user_embedding"])
            
            # Calculate similarity with AI response
            ai_sim = cosine_similarity(query_embedding, conv["ai_embedding"])
            
            # Use the higher similarity
            max_sim = max(user_sim, ai_sim)
            
            if max_sim >= similarity_threshold:
                similarities.append({
                    "index": i,
                    "similarity": max_sim,
                    "conversation": conv
                })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Return top results
        results = []
        for sim_data in similarities[:max_results]:
            conv = sim_data["conversation"]
            results.append({
                "user_message": conv["user_message"],
                "ai_response": conv["ai_response"],
                "similarity": sim_data["similarity"],
                "date": conv["date"]
            })
        
        return results
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"RAG search error: {e}")
        return []


def get_rag_context(current_message: str) -> str:
    """Get RAG context for current message"""
    if not rag_enabled:
        return ""
    
    try:
        similar_conversations = search_similar_conversations(current_message, max_results=3)
        
        if not similar_conversations:
            return ""
        
        context_parts = ["Relevant past conversations:"]
        
        for i, conv in enumerate(similar_conversations):
            similarity_pct = int(conv["similarity"] * 100)
            context_parts.append(f"{i+1}. User: {conv['user_message']}")
            context_parts.append(f"   AI: {conv['ai_response']} (similarity: {similarity_pct}%)")
        
        return "\n".join(context_parts)
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error getting RAG context: {e}")
        return ""


def update_rag_from_conversations():
    """Update RAG system from conversation log"""
    global is_updating
    
    if is_updating or not rag_enabled:
        return
    
    is_updating = True
    
    try:
        utils.zw_logging.update_debug_log("Updating RAG from conversations...")
        
        # Load conversation log
        if not os.path.exists('LiveLog.json'):
            return
        
        with open('LiveLog.json', 'r', encoding='utf-8') as f:
            conversations = json.load(f)
        
        # Get existing conversation count
        existing_count = len(conversation_index)
        
        # Process new conversations
        new_conversations = conversations[existing_count:]
        
        for conv in new_conversations:
            if len(conv) >= 2:
                add_conversation_to_rag(conv[0], conv[1])
        
        # Save updated RAG data
        save_rag_data()
        
        if new_conversations:
            utils.zw_logging.update_debug_log(f"Updated RAG with {len(new_conversations)} new conversations")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"RAG update error: {e}")
    finally:
        is_updating = False


def load_rag_data():
    """Load RAG data from files"""
    global conversation_index
    
    try:
        rag_dir = "Configurables/RAG"
        utils.cane_lib.ensure_directory(rag_dir)
        
        rag_file = os.path.join(rag_dir, "rag_index.json")
        conversation_index = utils.cane_lib.safe_json_load(rag_file, [])
        
        utils.zw_logging.update_debug_log(f"Loaded {len(conversation_index)} RAG entries")
        
        # Update from conversations if RAG is empty
        if not conversation_index:
            update_rag_from_conversations()
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error loading RAG data: {e}")
        conversation_index = []


def save_rag_data():
    """Save RAG data to files"""
    try:
        rag_dir = "Configurables/RAG"
        utils.cane_lib.ensure_directory(rag_dir)
        
        rag_file = os.path.join(rag_dir, "rag_index.json")
        utils.cane_lib.safe_json_save(rag_file, conversation_index)
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error saving RAG data: {e}")


def rebuild_rag_index():
    """Rebuild the entire RAG index"""
    global conversation_index, is_updating
    
    if is_updating:
        return False
    
    is_updating = True
    
    try:
        utils.zw_logging.update_debug_log("Rebuilding RAG index...")
        
        # Clear existing index
        conversation_index = []
        
        # Rebuild from conversation log
        update_rag_from_conversations()
        
        utils.zw_logging.update_debug_log("RAG index rebuild completed")
        return True
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"RAG rebuild error: {e}")
        return False
    finally:
        is_updating = False


def get_rag_stats():
    """Get RAG system statistics"""
    return {
        "enabled": rag_enabled,
        "total_conversations": len(conversation_index),
        "similarity_threshold": similarity_threshold,
        "max_entries": max_rag_entries,
        "is_initialized": is_rag_initialized,
        "is_updating": is_updating
    }


def clear_rag_data():
    """Clear all RAG data"""
    global conversation_index
    
    try:
        conversation_index = []
        save_rag_data()
        utils.zw_logging.update_debug_log("RAG data cleared")
        return True
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error clearing RAG data: {e}")
        return False


def set_similarity_threshold(threshold: float):
    """Set similarity threshold for RAG searches"""
    global similarity_threshold
    
    similarity_threshold = max(0.0, min(1.0, threshold))
    utils.zw_logging.update_debug_log(f"RAG similarity threshold set to: {similarity_threshold}")


# Initialize on import
initialize()
