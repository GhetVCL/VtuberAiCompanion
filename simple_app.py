"""
Enhanced Z-Waif AI VTuber Application
Advanced memory, RAG, streaming, and Discord integration with Gemini 2.5 Flash
"""

import os
import sys
import threading
import time
import json
import gradio as gr
from dotenv import load_dotenv
import google.generativeai as genai
import asyncio
import uuid
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize database first
try:
    from models import init_database
    init_database()
    print("Database initialized")
except Exception as e:
    print(f"Database initialization warning: {e}")

# Import enhanced systems
try:
    from memory_rag_system import memory_rag_system
    from streaming_system import streaming_manager
    from discord_integration import discord_manager
    print("Enhanced systems imported successfully")
except Exception as e:
    print(f"Warning: Enhanced systems not available: {e}")
    memory_rag_system = None
    streaming_manager = None
    discord_manager = None

# Configuration
class Config:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.char_name = os.getenv("CHAR_NAME", "Lily")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self.web_ui_port = int(os.getenv("WEB_UI_PORT", "5000"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("MAX_TOKENS", "300"))

config = Config()

# Character data
character_data = {
    "name": "Lily",
    "description": "A friendly AI VTuber powered by Gemini 2.5 Flash",
    "personality": [
        "Cheerful and enthusiastic",
        "Helpful and supportive", 
        "Curious about the world",
        "Enjoys chatting with viewers",
        "Mischievous and funny",
        "Occasionally uses cute expressions",
        "Tech-savvy and knowledgeable",
        "Empathetic and understanding"
    ],
    "speaking_style": [
        "Uses casual, friendly language",
        "Occasionally adds cute expressions like 'nya~' or '♪'",
        "Asks engaging follow-up questions",
        "Shows enthusiasm for topics she finds interesting"
    ]
}

# Conversation history
conversation_history = []
last_response = ""

class GeminiController:
    def __init__(self):
        self.model = None
        self.chat_session = None
        self.initialize()
    
    def initialize(self):
        """Initialize Gemini API"""
        if not config.gemini_api_key:
            print("❌ GEMINI_API_KEY not found in environment variables")
            return False
        
        try:
            genai.configure(api_key=config.gemini_api_key)
            
            generation_config = {
                "temperature": config.temperature,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": config.max_tokens,
                "response_mime_type": "text/plain",
            }
            
            self.model = genai.GenerativeModel(
                model_name=config.model_name,
                generation_config=generation_config,
                system_instruction=self.build_character_prompt()
            )
            
            self.chat_session = self.model.start_chat(history=[])
            print(f"✅ Gemini {config.model_name} initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error initializing Gemini: {e}")
            return False
    
    def build_character_prompt(self):
        """Build character prompt"""
        prompt = f"""You are {character_data['name']}, {character_data['description']}.

Your personality traits:
{chr(10).join(f"- {trait}" for trait in character_data['personality'])}

Your speaking style:
{chr(10).join(f"- {style}" for style in character_data['speaking_style'])}

Guidelines:
- Stay in character as {character_data['name']}
- Be helpful, friendly, and engaging
- Use natural conversation flow
- Show genuine interest in the user's topics
- Keep responses conversational and not too long
- You can use cute expressions occasionally but don't overdo it
"""
        return prompt
    
    def send_message(self, user_input: str, user_id: str = "web_user") -> str:
        """Send message to Gemini with enhanced memory integration"""
        global last_response, conversation_history
        
        if not self.chat_session:
            return "Sorry, I'm having trouble connecting to my AI brain right now."
        
        try:
            # Get enhanced context if memory system is available
            enhanced_prompt = user_input
            if memory_rag_system:
                context = memory_rag_system.build_context_for_response(user_input, user_id)
                if context:
                    enhanced_prompt = f"{context}\nUser message: {user_input}\n\nRespond as Aria using the context above for personalization."
            
            response = self.chat_session.send_message(enhanced_prompt)
            last_response = response.text
            
            # Store in enhanced memory system if available
            if memory_rag_system:
                memory_rag_system.store_conversation(
                    user_id=user_id,
                    user_message=user_input,
                    ai_response=last_response,
                    platform='web'
                )
                
                # Update user profile
                context_data = memory_rag_system._extract_context(user_input, last_response)
                memory_rag_system.update_user_profile(user_id, context_data)
            
            # Add to conversation history
            conversation_history.append([user_input, last_response])
            
            # Keep only last 20 exchanges
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
            
            # Save conversation
            self.save_conversation()
            
            return last_response
            
        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            print(f"❌ Gemini API error: {e}")
            return error_msg
    
    def save_conversation(self):
        """Save conversation to file"""
        try:
            with open('LiveLog.json', 'w', encoding='utf-8') as f:
                json.dump(conversation_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Could not save conversation: {e}")

# Initialize Gemini controller
gemini = GeminiController()

def create_web_ui():
    """Create Enhanced Gradio web interface with advanced features"""
    
    def chat_function(message, history, user_id):
        if not message.strip():
            return history, "", ""
        
        # Generate unique user ID if not provided
        if not user_id:
            user_id = f"web_user_{uuid.uuid4().hex[:8]}"
        
        # Get AI response with memory integration
        response = gemini.send_message(message, user_id)
        
        # Add to history
        history.append([message, response])
        
        # Get memory stats for display
        memory_info = ""
        if memory_rag_system:
            stats = memory_rag_system.get_conversation_stats(user_id)
            memory_info = f"Conversations: {stats.get('total_conversations', 0)} | Memories: {stats.get('total_memories', 0)}"
        
        return history, "", memory_info
    
    def regenerate_last(history, user_id):
        """Regenerate last response with memory context"""
        if not history:
            return history, ""
        
        if not user_id:
            user_id = f"web_user_{uuid.uuid4().hex[:8]}"
        
        last_user_msg = history[-1][0] if history else ""
        
        if last_user_msg:
            # Regenerate with memory context
            response = gemini.send_message(f"Please provide a different response to: {last_user_msg}", user_id)
            history[-1][1] = response
        
        # Update memory stats
        memory_info = ""
        if memory_rag_system:
            stats = memory_rag_system.get_conversation_stats(user_id)
            memory_info = f"Conversations: {stats.get('total_conversations', 0)} | Memories: {stats.get('total_memories', 0)}"
        
        return history, memory_info
    
    def get_user_memories(user_id):
        """Get user's stored memories"""
        if not memory_rag_system or not user_id:
            return "Memory system not available or no user ID provided"
        
        try:
            memories = memory_rag_system.get_relevant_memories("", user_id, max_results=10)
            if not memories:
                return "No memories found for this user"
            
            memory_text = "Recent Memories:\n"
            for i, mem in enumerate(memories, 1):
                memory_text += f"{i}. {mem['content']} (Type: {mem['type']}, Score: {mem['importance']:.1f})\n"
            
            return memory_text
        except Exception as e:
            return f"Error retrieving memories: {e}"
    
    def get_system_status():
        """Get overall system status"""
        status_info = []
        
        # Gemini status
        status_info.append(f"🤖 AI Model: {'Connected' if gemini.model else 'Disconnected'}")
        
        # Memory system status
        if memory_rag_system:
            total_stats = memory_rag_system.get_conversation_stats()
            status_info.append(f"🧠 Memory: {total_stats.get('total_conversations', 0)} conversations, {total_stats.get('total_memories', 0)} memories")
        else:
            status_info.append("🧠 Memory: Not available")
        
        # Streaming status
        if streaming_manager:
            stream_stats = streaming_manager.get_active_sessions()
            status_info.append(f"📡 Streaming: {stream_stats.get('total_connections', 0)} active connections")
        else:
            status_info.append("📡 Streaming: Not available")
        
        # Discord status
        if discord_manager:
            discord_status = discord_manager.get_bot_status()
            status_info.append(f"💬 Discord: {discord_status.get('status', 'unknown')} - {discord_status.get('guilds', 0)} servers")
        else:
            status_info.append("💬 Discord: Not available")
        
        return "\n".join(status_info)
    
    # Create interface
    with gr.Blocks(
        title=f"{character_data['name']} - AI VTuber",
        theme=gr.themes.Soft(primary_hue="blue")
    ) as interface:
        
        gr.Markdown(f"# 🎭 {character_data['name']} - AI VTuber")
        gr.Markdown(f"*{character_data['description']}*")
        gr.Markdown("Powered by **Gemini 2.5 Flash Experimental**")
        
        with gr.Row():
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(
                    value=conversation_history[-10:] if conversation_history else [],
                    height=500,
                    label="Conversation",
                    show_label=False
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder=f"Chat with {character_data['name']}...",
                        label="Message",
                        scale=4,
                        container=False
                    )
                    send_btn = gr.Button("Send", scale=1, variant="primary")
                    regen_btn = gr.Button("🔄", scale=1, variant="secondary")
            
            with gr.Column(scale=1):
                gr.Markdown("### Settings")
                
                status_text = gr.Textbox(
                    value="🟢 Connected" if gemini.model else "🔴 Disconnected",
                    label="Status",
                    interactive=False
                )
                
                model_text = gr.Textbox(
                    value=config.model_name,
                    label="AI Model",
                    interactive=False
                )
                
                temp_slider = gr.Slider(
                    minimum=0.1,
                    maximum=2.0,
                    value=config.temperature,
                    step=0.1,
                    label="Temperature",
                    interactive=False
                )
                
                tokens_slider = gr.Slider(
                    minimum=50,
                    maximum=1000,
                    value=config.max_tokens,
                    step=50,
                    label="Max Tokens",
                    interactive=False
                )
                
                gr.Markdown("### Character Info")
                char_info = gr.Textbox(
                    value=f"Name: {character_data['name']}\nPersonality: Friendly AI VTuber\nPowered by: Gemini 2.5 Flash",
                    lines=4,
                    label="Character",
                    interactive=False
                )
        
        # Event handlers
        send_btn.click(
            chat_function,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        )
        
        msg_input.submit(
            chat_function,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        )
        
        regen_btn.click(
            lambda: regenerate_last(),
            outputs=[chatbot]
        )
    
    return interface

def main():
    """Main application entry point"""
    print("🌟 Starting Z-Waif AI VTuber System...")
    print(f"Character: {config.char_name}")
    print(f"Model: {config.model_name}")
    print(f"Port: {config.web_ui_port}")
    print()
    
    if not config.gemini_api_key:
        print("❌ Missing GEMINI_API_KEY in environment variables")
        print("Please add your Gemini API key to the .env file")
        return
    
    if not gemini.model:
        print("❌ Failed to initialize Gemini API")
        return
    
    # Create and launch web interface
    print("🌐 Starting Web Interface...")
    interface = create_web_ui()
    
    try:
        interface.launch(
            server_name="0.0.0.0",
            server_port=config.web_ui_port,
            share=False,
            quiet=True,
            show_error=True
        )
    except Exception as e:
        print(f"❌ Error starting web interface: {e}")

if __name__ == "__main__":
    main()