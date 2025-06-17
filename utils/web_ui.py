import gradio as gr
import threading
import time
import json
import utils.settings
import utils.zw_logging
import API.gemini_controller
import API.character_card
import main

# Global UI variables
chat_interface = None
chat_history = []
is_ui_running = False

def start_ui():
    """Start the Gradio web UI"""
    global is_ui_running
    
    if not utils.settings.web_ui_enabled:
        return
    
    ui_thread = threading.Thread(target=launch_ui)
    ui_thread.daemon = True
    ui_thread.start()
    
    is_ui_running = True
    utils.zw_logging.update_debug_log("Web UI started")


def launch_ui():
    """Launch the Gradio interface"""
    global chat_interface
    
    # Load chat history
    load_chat_history()
    
    # Create the interface
    with gr.Blocks(
        title="Z-Waif AI VTuber",
        theme=gr.themes.Soft(primary_hue=utils.settings.primary_color)
    ) as chat_interface:
        
        gr.Markdown("# Z-Waif AI VTuber Interface")
        gr.Markdown("Chat with your AI VTuber using Gemini 2.5 Flash!")
        
        # Chat interface
        with gr.Row():
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(
                    value=chat_history,
                    height=400,
                    label="Conversation"
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Type your message here...",
                        label="Message",
                        scale=4
                    )
                    send_btn = gr.Button("Send", scale=1, variant="primary")
                    next_btn = gr.Button("Regenerate", scale=1)
        
        # Settings panel
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Settings")
                
                vtube_toggle = gr.Checkbox(
                    value=utils.settings.vtube_enabled,
                    label="VTube Studio"
                )
                
                stream_toggle = gr.Checkbox(
                    value=utils.settings.stream_chats,
                    label="Stream Responses"
                )
                
                speak_toggle = gr.Checkbox(
                    value=not utils.settings.only_speak_when_spoken_to,
                    label="Auto Speak"
                )
                
                temp_slider = gr.Slider(
                    minimum=0.1,
                    maximum=2.0,
                    value=utils.settings.temperature,
                    step=0.1,
                    label="Temperature"
                )
                
                tokens_slider = gr.Slider(
                    minimum=50,
                    maximum=1000,
                    value=utils.settings.max_tokens,
                    step=50,
                    label="Max Tokens"
                )
        
        # Character info panel
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Character Information")
                char_info = gr.Textbox(
                    value=get_character_info(),
                    label="Character Details",
                    lines=3,
                    interactive=False
                )
        
        # Event handlers
        def send_message(message, history):
            if not message.strip():
                return history, ""
            
            # Add user message to history
            history.append([message, ""])
            
            # Send to AI
            main.main_web_ui_chat(message)
            
            # Get response
            response = API.gemini_controller.get_last_response()
            
            # Update history with response
            history[-1][1] = response
            
            # Save chat history
            save_chat_history(history)
            
            return history, ""
        
        def regenerate_response(history):
            if not history:
                return history
            
            # Get last user message
            last_message = history[-1][0] if history else ""
            
            if last_message:
                # Regenerate response
                main.main_web_ui_next()
                response = API.gemini_controller.get_last_response()
                
                # Update last response in history
                history[-1][1] = response
                
                # Save chat history
                save_chat_history(history)
            
            return history
        
        def update_setting(setting_name, value):
            utils.settings.set_setting(setting_name, value)
            utils.settings.save_settings()
        
        # Connect events
        send_btn.click(
            send_message,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        )
        
        msg_input.submit(
            send_message,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        )
        
        next_btn.click(
            regenerate_response,
            inputs=[chatbot],
            outputs=[chatbot]
        )
        
        # Settings event handlers
        vtube_toggle.change(
            lambda x: update_setting("vtube_enabled", x),
            inputs=[vtube_toggle]
        )
        
        stream_toggle.change(
            lambda x: update_setting("stream_chats", x),
            inputs=[stream_toggle]
        )
        
        speak_toggle.change(
            lambda x: update_setting("only_speak_when_spoken_to", not x),
            inputs=[speak_toggle]
        )
        
        temp_slider.change(
            lambda x: update_setting("temperature", x),
            inputs=[temp_slider]
        )
        
        tokens_slider.change(
            lambda x: update_setting("max_tokens", int(x)),
            inputs=[tokens_slider]
        )
    
    # Launch the interface
    chat_interface.launch(
        server_name="0.0.0.0",
        server_port=utils.settings.web_ui_port,
        share=False,
        quiet=True
    )


def load_chat_history():
    """Load chat history from file"""
    global chat_history
    
    try:
        with open('LiveLog.json', 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        # Convert log format to UI format
        chat_history = []
        for entry in log_data[-10:]:  # Last 10 exchanges
            if len(entry) >= 2:
                chat_history.append([entry[0], entry[1]])
        
    except (FileNotFoundError, json.JSONDecodeError):
        chat_history = []


def save_chat_history(history):
    """Save chat history to file"""
    try:
        # Convert UI format to log format
        log_data = []
        for entry in history:
            if len(entry) >= 2 and entry[0] and entry[1]:
                log_data.append([entry[0], entry[1]])
        
        with open('LiveLog.json', 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error saving chat history: {e}")


def get_character_info():
    """Get character information for display"""
    char_data = API.character_card.get_character_data()
    
    info_parts = []
    info_parts.append(f"Name: {char_data.get('name', 'Unknown')}")
    info_parts.append(f"Description: {char_data.get('description', 'No description')}")
    
    personality = char_data.get('personality', [])
    if personality:
        info_parts.append(f"Personality: {', '.join(personality[:3])}")
    
    return "\n".join(info_parts)


def update_ui_chat_history():
    """Update UI chat history with latest conversation"""
    if chat_interface and is_ui_running:
        load_chat_history()


def get_ui_status():
    """Get UI status"""
    return {
        "running": is_ui_running,
        "port": utils.settings.web_ui_port,
        "url": f"http://localhost:{utils.settings.web_ui_port}"
    }


def stop_ui():
    """Stop the web UI"""
    global is_ui_running
    is_ui_running = False
    if chat_interface:
        chat_interface.close()
    utils.zw_logging.update_debug_log("Web UI stopped")
