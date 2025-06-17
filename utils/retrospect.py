"""
Retrospect System - Handles conversation analysis and memory formation
Analyzes past conversations to form long-term memories and insights
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import utils.zw_logging
import utils.cane_lib
import API.gemini_controller

# Retrospect variables
retrospect_enabled = True
analysis_interval = 3600  # 1 hour
last_analysis_time = 0
memory_insights = []
conversation_summaries = []
retrospect_thread = None
is_retrospect_running = False

def initialize():
    """Initialize retrospect system"""
    global retrospect_enabled, is_retrospect_running, retrospect_thread
    
    retrospect_enabled = os.getenv("RETROSPECT_ENABLED", "true").lower() == "true"
    
    if not retrospect_enabled:
        utils.zw_logging.update_debug_log("Retrospect system disabled")
        return
    
    load_retrospect_data()
    
    # Start retrospect analysis thread
    is_retrospect_running = True
    retrospect_thread = threading.Thread(target=retrospect_analysis_loop)
    retrospect_thread.daemon = True
    retrospect_thread.start()
    
    utils.zw_logging.update_debug_log("Retrospect system initialized")


def retrospect_analysis_loop():
    """Background retrospect analysis loop"""
    global last_analysis_time
    
    while is_retrospect_running:
        try:
            current_time = time.time()
            
            # Check if it's time for analysis
            if current_time - last_analysis_time >= analysis_interval:
                analyze_recent_conversations()
                last_analysis_time = current_time
            
            # Sleep for 5 minutes before checking again
            time.sleep(300)
            
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Retrospect analysis loop error: {e}")
            time.sleep(600)  # Sleep longer on error


def analyze_recent_conversations():
    """Analyze recent conversations for insights"""
    try:
        # Load recent conversation history
        recent_conversations = get_recent_conversations(hours=24)
        
        if len(recent_conversations) < 3:
            utils.zw_logging.update_debug_log("Not enough recent conversations for analysis")
            return
        
        # Generate summary and insights
        summary = generate_conversation_summary(recent_conversations)
        insights = extract_conversation_insights(recent_conversations)
        
        if summary:
            add_conversation_summary(summary)
        
        if insights:
            for insight in insights:
                add_memory_insight(insight)
        
        utils.zw_logging.update_debug_log(f"Analyzed {len(recent_conversations)} recent conversations")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Conversation analysis error: {e}")


def get_recent_conversations(hours: int = 24) -> List[List[str]]:
    """Get conversations from the last N hours"""
    try:
        if not os.path.exists('LiveLog.json'):
            return []
        
        with open('LiveLog.json', 'r', encoding='utf-8') as f:
            all_conversations = json.load(f)
        
        # For simplicity, return last N conversations
        # In a real implementation, you'd filter by timestamp
        recent_count = min(len(all_conversations), 20)
        return all_conversations[-recent_count:]
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error loading recent conversations: {e}")
        return []


def generate_conversation_summary(conversations: List[List[str]]) -> Optional[str]:
    """Generate a summary of recent conversations"""
    if not conversations:
        return None
    
    try:
        # Prepare conversation text for analysis
        conversation_text = ""
        for conv in conversations[-10:]:  # Last 10 conversations
            if len(conv) >= 2:
                conversation_text += f"User: {conv[0]}\nAI: {conv[1]}\n\n"
        
        if not conversation_text.strip():
            return None
        
        # Generate summary prompt
        summary_prompt = f"""
        Please provide a brief summary of these recent conversations, focusing on:
        1. Main topics discussed
        2. User's interests and preferences
        3. Any recurring themes
        4. Notable moments or interactions
        
        Conversations:
        {conversation_text}
        
        Provide a concise summary in 2-3 sentences.
        """
        
        # Use AI to generate summary
        API.gemini_controller.send_message(summary_prompt)
        summary = API.gemini_controller.get_last_response()
        
        return summary if summary else None
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Summary generation error: {e}")
        return None


def extract_conversation_insights(conversations: List[List[str]]) -> List[str]:
    """Extract insights from conversations"""
    insights = []
    
    try:
        # Analyze conversation patterns
        user_topics = []
        user_questions = []
        conversation_lengths = []
        
        for conv in conversations:
            if len(conv) >= 2:
                user_msg = conv[0].lower()
                ai_msg = conv[1]
                
                # Extract topics (simple keyword analysis)
                if any(keyword in user_msg for keyword in ['game', 'gaming', 'play']):
                    user_topics.append('gaming')
                if any(keyword in user_msg for keyword in ['music', 'song', 'sing']):
                    user_topics.append('music')
                if any(keyword in user_msg for keyword in ['help', 'question', 'how']):
                    user_topics.append('help-seeking')
                
                # Check for questions
                if '?' in user_msg:
                    user_questions.append(user_msg)
                
                # Track conversation length
                conversation_lengths.append(len(user_msg.split()) + len(ai_msg.split()))
        
        # Generate insights
        if user_topics:
            top_topics = list(set(user_topics))
            if len(top_topics) <= 3:
                insights.append(f"User shows interest in: {', '.join(top_topics)}")
        
        if len(user_questions) > len(conversations) * 0.3:
            insights.append("User frequently asks questions - enjoys learning and exploring topics")
        
        if conversation_lengths:
            avg_length = sum(conversation_lengths) / len(conversation_lengths)
            if avg_length > 50:
                insights.append("User engages in detailed, lengthy conversations")
            elif avg_length < 20:
                insights.append("User prefers brief, concise interactions")
        
        return insights
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Insight extraction error: {e}")
        return []


def add_memory_insight(insight: str):
    """Add a new memory insight"""
    global memory_insights
    
    try:
        insight_entry = {
            "content": insight,
            "timestamp": time.time(),
            "date": datetime.now().isoformat(),
            "type": "insight"
        }
        
        memory_insights.append(insight_entry)
        
        # Keep only recent insights (last 100)
        if len(memory_insights) > 100:
            memory_insights = memory_insights[-100:]
        
        save_retrospect_data()
        utils.zw_logging.update_debug_log(f"Added memory insight: {insight}")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error adding memory insight: {e}")


def add_conversation_summary(summary: str):
    """Add a conversation summary"""
    global conversation_summaries
    
    try:
        summary_entry = {
            "content": summary,
            "timestamp": time.time(),
            "date": datetime.now().isoformat(),
            "period": "24h"
        }
        
        conversation_summaries.append(summary_entry)
        
        # Keep only recent summaries (last 30)
        if len(conversation_summaries) > 30:
            conversation_summaries = conversation_summaries[-30:]
        
        save_retrospect_data()
        utils.zw_logging.update_debug_log("Added conversation summary")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error adding conversation summary: {e}")


def get_relevant_memories(context: str) -> str:
    """Get relevant memories for current context"""
    if not retrospect_enabled:
        return ""
    
    try:
        relevant_memories = []
        context_lower = context.lower()
        
        # Check insights for relevance
        for insight in memory_insights[-20:]:  # Recent insights
            insight_content = insight.get("content", "").lower()
            # Simple relevance check
            if any(word in insight_content for word in context_lower.split() if len(word) > 3):
                relevant_memories.append(f"Insight: {insight['content']}")
        
        # Check summaries for relevance
        for summary in conversation_summaries[-5:]:  # Recent summaries
            summary_content = summary.get("content", "").lower()
            if any(word in summary_content for word in context_lower.split() if len(word) > 3):
                relevant_memories.append(f"Summary: {summary['content']}")
        
        if relevant_memories:
            return "Relevant memories:\n" + "\n".join(relevant_memories[:3])  # Max 3 memories
        
        return ""
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error retrieving relevant memories: {e}")
        return ""


def load_retrospect_data():
    """Load retrospect data from files"""
    global memory_insights, conversation_summaries
    
    try:
        retrospect_dir = "Configurables/Retrospect"
        utils.cane_lib.ensure_directory(retrospect_dir)
        
        # Load insights
        insights_file = os.path.join(retrospect_dir, "insights.json")
        memory_insights = utils.cane_lib.safe_json_load(insights_file, [])
        
        # Load summaries
        summaries_file = os.path.join(retrospect_dir, "summaries.json")
        conversation_summaries = utils.cane_lib.safe_json_load(summaries_file, [])
        
        utils.zw_logging.update_debug_log(f"Loaded {len(memory_insights)} insights and {len(conversation_summaries)} summaries")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error loading retrospect data: {e}")


def save_retrospect_data():
    """Save retrospect data to files"""
    try:
        retrospect_dir = "Configurables/Retrospect"
        utils.cane_lib.ensure_directory(retrospect_dir)
        
        # Save insights
        insights_file = os.path.join(retrospect_dir, "insights.json")
        utils.cane_lib.safe_json_save(insights_file, memory_insights)
        
        # Save summaries
        summaries_file = os.path.join(retrospect_dir, "summaries.json")
        utils.cane_lib.safe_json_save(summaries_file, conversation_summaries)
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error saving retrospect data: {e}")


def get_retrospect_stats():
    """Get retrospect system statistics"""
    return {
        "enabled": retrospect_enabled,
        "total_insights": len(memory_insights),
        "total_summaries": len(conversation_summaries),
        "last_analysis": last_analysis_time,
        "next_analysis": last_analysis_time + analysis_interval
    }


def force_analysis():
    """Force immediate conversation analysis"""
    global last_analysis_time
    
    try:
        analyze_recent_conversations()
        last_analysis_time = time.time()
        utils.zw_logging.update_debug_log("Forced retrospect analysis completed")
        return True
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Forced analysis error: {e}")
        return False


def stop_retrospect():
    """Stop the retrospect system"""
    global is_retrospect_running
    is_retrospect_running = False
    utils.zw_logging.update_debug_log("Retrospect system stopped")


# Initialize on import
initialize()
