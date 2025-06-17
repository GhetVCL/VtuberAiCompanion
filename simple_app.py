"""
Simplified Z-Waif AI VTuber Application
Core functionality with Gemini 2.5 Flash integration
"""

import os
import sys
import threading
import time
import json
import gradio as gr
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configuration
class Config:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.char_name = os.getenv("CHAR_NAME", "Aria")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self.web_ui_port = int(os.getenv("WEB_UI_PORT", "5000"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("MAX_TOKENS", "300"))

config = Config()

# Character data
character_data = {
    "name": "Aria",
    "description": "A friendly AI VTuber assistant powered by Gemini 2.5 Flash",
    "personality": [
        "Cheerful and enthusiastic",
        "Helpful and supportive", 
        "Curious about the world",
        "Enjoys chatting with viewers",
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
    
    def send_message(self, user_input: str) -> str:
        """Send message to Gemini and get response"""
        global last_response, conversation_history
        
        if not self.chat_session:
            return "Sorry, I'm having trouble connecting to my AI brain right now."
        
        try:
            response = self.chat_session.send_message(user_input)
            last_response = response.text
            
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
    """Create Gradio web interface"""
    
    def chat_function(message, history):
        if not message.strip():
            return history, ""
        
        # Get AI response
        response = gemini.send_message(message)
        
        # Add to history
        history.append([message, response])
        
        return history, ""
    
    def regenerate_last():
        """Regenerate last response"""
        if conversation_history:
            last_user_msg = conversation_history[-1][0]
            response = gemini.send_message(f"Please provide a different response to: {last_user_msg}")
            conversation_history[-1][1] = response
            return conversation_history
        return conversation_history
    
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