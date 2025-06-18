"""
Z-Waif AI VTuber Application Entry Point
Alternative entry point that starts the web UI and main system
"""

import os
import sys
import threading
import time
import webbrowser
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import main
    import utils.web_ui
    import utils.settings
    import utils.zw_logging
except ImportError as e:
    print(f"Warning: Some modules not available: {e}")
    # Create minimal fallbacks
    class MockLogging:
        @staticmethod
        def update_debug_log(msg): print(f"[DEBUG] {msg}")
        @staticmethod
        def log_error(msg): print(f"[ERROR] {msg}")
    
    class MockSettings:
        web_ui_enabled = True
        web_ui_port = 5000
        vtube_enabled = False
        discord_enabled = False
        
        @staticmethod
        def load_settings(): pass
    
    utils = type('utils', (), {})()
    utils.zw_logging = MockLogging()
    utils.settings = MockSettings()
    utils.web_ui = None

def start_application():
    """Start the Z-Waif application with web UI"""
    try:
        print("🌟 Starting Z-Waif AI VTuber System...")
        
        # Initialize logging
        utils.zw_logging.update_debug_log("Z-Waif application starting...")
        
        # Load settings
        utils.settings.load_settings()
        
        # Start web UI in background
        if utils.settings.web_ui_enabled:
            print("🌐 Starting Web UI...")
            ui_thread = threading.Thread(target=utils.web_ui.start_ui)
            ui_thread.daemon = True
            ui_thread.start()
            
            # Wait a moment for UI to start
            time.sleep(2)
            
            # Open browser if in desktop environment
            try:
                ui_url = f"http://localhost:{utils.settings.web_ui_port}"
                print(f"📱 Web UI available at: {ui_url}")
                
                # Uncomment to auto-open browser
                # webbrowser.open(ui_url)
                
            except Exception as e:
                print(f"Note: Could not auto-open browser: {e}")
        
        # Start main application
        print("🎤 Starting voice interaction system...")
        main.main()
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down Z-Waif...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        utils.zw_logging.log_error(f"Application startup error: {e}")
        sys.exit(1)


def check_requirements():
    """Check if required environment variables are set"""
    required_env_vars = [
        "GEMINI_API_KEY",
        "CHAR_NAME"
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease check your .env file and ensure all required variables are set.")
        return False
    
    return True


def show_welcome_message():
    """Show welcome message and system info"""
    print("=" * 60)
    print("  🎭 Z-Waif AI VTuber System")
    print("  Powered by Gemini 2.5 Flash")
    print("=" * 60)
    print()
    
    # Show configuration
    char_name = os.getenv("CHAR_NAME", "Lily")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
    
    print(f"Character: {char_name}")
    print(f"AI Model: {model}")
    print(f"Web UI Port: {utils.settings.web_ui_port}")
    print(f"VTube Studio: {'Enabled' if utils.settings.vtube_enabled else 'Disabled'}")
    print(f"Discord: {'Enabled' if utils.settings.discord_enabled else 'Disabled'}")
    print()


if __name__ == "__main__":
    # Show welcome message
    show_welcome_message()
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Start application
    start_application()
