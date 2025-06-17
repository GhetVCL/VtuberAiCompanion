import os
import time
import json
import threading
import google.generativeai as genai
from typing import List, Dict, Any, Optional, Generator
import utils.settings
import utils.zw_logging
import API.character_card

# Global variables
conversation_history: List[Dict[str, str]] = []
last_response: str = ""
last_message_streamed: bool = False
is_generating: bool = False
should_stop_generation: bool = False
current_model = None
generation_config = None

def initialize():
    """Initialize the Gemini API client"""
    global current_model, generation_config
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    genai.configure(api_key=api_key)
    
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
    current_model = genai.GenerativeModel(model_name)
    
    # Configure generation parameters
    generation_config = genai.types.GenerationConfig(
        temperature=float(os.getenv("TEMPERATURE", "0.7")),
        top_p=float(os.getenv("TOP_P", "0.9")),
        max_output_tokens=int(os.getenv("MAX_TOKENS", "300")),
        candidate_count=1,
    )
    
    utils.zw_logging.update_debug_log(f"Gemini API initialized with model: {model_name}")
    print(f"Gemini API ready with model: {model_name}")


def build_conversation_context() -> str:
    """Build the conversation context including character card and history"""
    character_info = API.character_card.get_character_prompt()
    
    context_parts = [
        "You are an AI VTuber assistant. Follow these guidelines:",
        character_info,
        "",
        "Current conversation history:"
    ]
    
    # Add recent conversation history (last 10 exchanges)
    recent_history = conversation_history[-20:] if len(conversation_history) > 20 else conversation_history
    
    for entry in recent_history:
        if entry['role'] == 'user':
            context_parts.append(f"User: {entry['content']}")
        else:
            context_parts.append(f"Assistant: {entry['content']}")
    
    return "\n".join(context_parts)


def send_message(user_input: str) -> None:
    """Send a message to Gemini and handle the response"""
    global conversation_history, last_response, last_message_streamed, is_generating
    
    try:
        # Add user message to history
        conversation_history.append({"role": "user", "content": user_input})
        
        # Build context
        context = build_conversation_context()
        
        is_generating = True
        
        if utils.settings.stream_chats:
            # Stream the response
            last_message_streamed = True
            response_text = _stream_response(context, user_input)
        else:
            # Generate complete response
            last_message_streamed = False
            response_text = _generate_complete_response(context, user_input)
        
        # Clean up the response
        response_text = _clean_response(response_text)
        
        # Add assistant response to history
        conversation_history.append({"role": "assistant", "content": response_text})
        last_response = response_text
        
        # Save conversation to log
        _save_conversation_log()
        
        utils.zw_logging.update_debug_log(f"Gemini response generated: {len(response_text)} characters")
        
    except Exception as e:
        error_msg = f"Error generating Gemini response: {str(e)}"
        utils.zw_logging.update_debug_log(error_msg)
        last_response = "I'm having trouble thinking right now. Could you try again?"
        print(f"Gemini API Error: {e}")
    finally:
        is_generating = False


def _stream_response(context: str, user_input: str) -> str:
    """Stream response from Gemini"""
    global should_stop_generation, last_response
    
    try:
        prompt = f"{context}\n\nUser: {user_input}\nAssistant:"
        
        response_parts = []
        
        response = current_model.generate_content(
            prompt,
            generation_config=generation_config,
            stream=True
        )
        
        for chunk in response:
            if should_stop_generation:
                should_stop_generation = False
                break
                
            if chunk.text:
                response_parts.append(chunk.text)
                # Update last_response for real-time display
                last_response = ''.join(response_parts)
                
                # Optional: Handle streaming display here
                if utils.settings.stream_chats:
                    print(chunk.text, end='', flush=True)
        
        return ''.join(response_parts)
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Streaming error: {str(e)}")
        return "I'm having trouble with streaming. Let me try again."


def _generate_complete_response(context: str, user_input: str) -> str:
    """Generate complete response from Gemini"""
    try:
        prompt = f"{context}\n\nUser: {user_input}\nAssistant:"
        
        response = current_model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        return response.text if response.text else "I'm not sure how to respond to that."
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Generation error: {str(e)}")
        return "I'm having trouble generating a response right now."


def _clean_response(text: str) -> str:
    """Clean and format the response text"""
    if not text:
        return "I'm not sure how to respond to that."
    
    # Remove common prefixes that Gemini might add
    prefixes_to_remove = ["Assistant:", "AI:", "Response:", "Reply:"]
    for prefix in prefixes_to_remove:
        if text.strip().startswith(prefix):
            text = text.strip()[len(prefix):].strip()
    
    # Remove asterisks (as per z-waif settings)
    if utils.settings.remove_asterisks:
        text = text.replace("*", "")
    
    # Apply RP suppression if enabled
    if utils.settings.rp_suppression:
        # Remove roleplay actions in brackets or parentheses
        import re
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
    
    # Apply newline cut if enabled
    if utils.settings.newline_cut:
        lines = text.split('\n')
        text = lines[0] if lines else text
    
    return text.strip()


def get_last_response() -> str:
    """Get the last generated response"""
    return last_response


def regenerate_last_response() -> None:
    """Regenerate the last response"""
    global conversation_history
    
    if len(conversation_history) >= 2:
        # Remove the last assistant response
        if conversation_history[-1]['role'] == 'assistant':
            conversation_history.pop()
        
        # Get the last user message
        last_user_message = None
        for entry in reversed(conversation_history):
            if entry['role'] == 'user':
                last_user_message = entry['content']
                break
        
        if last_user_message:
            send_message(last_user_message)


def stop_generation() -> None:
    """Stop the current generation"""
    global should_stop_generation
    should_stop_generation = True


def set_max_tokens(max_tokens: int) -> None:
    """Set maximum tokens for generation"""
    global generation_config
    generation_config.max_output_tokens = max_tokens


def clear_conversation_history() -> None:
    """Clear the conversation history"""
    global conversation_history
    conversation_history = []
    utils.zw_logging.update_debug_log("Conversation history cleared")


def _save_conversation_log() -> None:
    """Save conversation to log file"""
    try:
        log_data = []
        
        # Convert conversation history to simple format
        user_message = ""
        assistant_message = ""
        
        for entry in conversation_history[-2:]:  # Get last exchange
            if entry['role'] == 'user':
                user_message = entry['content']
            elif entry['role'] == 'assistant':
                assistant_message = entry['content']
        
        if user_message and assistant_message:
            # Load existing log
            try:
                with open('LiveLog.json', 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                log_data = []
            
            # Add new exchange
            log_data.append([user_message, assistant_message])
            
            # Save updated log
            with open('LiveLog.json', 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
                
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error saving conversation log: {str(e)}")


def get_conversation_stats() -> Dict[str, Any]:
    """Get conversation statistics"""
    return {
        "total_exchanges": len(conversation_history) // 2,
        "is_generating": is_generating,
        "last_message_streamed": last_message_streamed,
        "model_name": os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
    }


# Legacy compatibility functions (for z-waif compatibility)
def send_via_oogabooga(message: str) -> None:
    """Legacy compatibility function"""
    send_message(message)


def receive_via_oogabooga() -> str:
    """Legacy compatibility function"""
    return get_last_response()


def next_message_oogabooga() -> None:
    """Legacy compatibility function"""
    regenerate_last_response()


def set_force_skip_streaming(skip: bool) -> None:
    """Legacy compatibility function"""
    if skip:
        stop_generation()


# Initialize on import
try:
    initialize()
except Exception as e:
    print(f"Warning: Could not initialize Gemini API: {e}")
    utils.zw_logging.update_debug_log(f"Gemini initialization failed: {e}")
