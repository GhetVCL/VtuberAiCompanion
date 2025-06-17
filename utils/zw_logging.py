import os
import time
import threading
from datetime import datetime

# Logging variables
log_file_path = "log.txt"
debug_log_path = "debug.log"
log_lock = threading.Lock()

def update_debug_log(message: str):
    """Update debug log with timestamped message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    with log_lock:
        try:
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            # Fallback to console if file logging fails
            print(f"Logging error: {e}")
            print(f"Debug: {message}")


def update_main_log(message: str):
    """Update main log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    with log_lock:
        try:
            with open(log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Main logging error: {e}")


def log_conversation(user_message: str, ai_response: str):
    """Log conversation exchange"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = f"\n--- Conversation [{timestamp}] ---\n"
    log_entry += f"User: {user_message}\n"
    log_entry += f"AI: {ai_response}\n"
    log_entry += "--- End Conversation ---\n"
    
    with log_lock:
        try:
            with open("conversation.log", 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            update_debug_log(f"Conversation logging error: {e}")


def log_error(error_message: str, error_type: str = "ERROR"):
    """Log error with type"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {error_type}: {error_message}\n"
    
    with log_lock:
        try:
            with open("error.log", 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception:
            pass
    
    # Also log to debug
    update_debug_log(f"{error_type}: {error_message}")


def clear_logs():
    """Clear all log files"""
    log_files = [log_file_path, debug_log_path, "conversation.log", "error.log"]
    
    for log_file in log_files:
        try:
            if os.path.exists(log_file):
                open(log_file, 'w').close()
        except Exception as e:
            print(f"Error clearing {log_file}: {e}")
    
    update_debug_log("Log files cleared")


def get_log_size(log_type: str = "debug"):
    """Get log file size"""
    log_files = {
        "debug": debug_log_path,
        "main": log_file_path,
        "conversation": "conversation.log",
        "error": "error.log"
    }
    
    log_file = log_files.get(log_type, debug_log_path)
    
    try:
        if os.path.exists(log_file):
            return os.path.getsize(log_file)
        return 0
    except Exception:
        return 0


def rotate_logs(max_size_mb: int = 10):
    """Rotate logs if they exceed max size"""
    max_size_bytes = max_size_mb * 1024 * 1024
    
    log_files = [debug_log_path, log_file_path, "conversation.log", "error.log"]
    
    for log_file in log_files:
        try:
            if os.path.exists(log_file) and os.path.getsize(log_file) > max_size_bytes:
                backup_name = f"{log_file}.backup"
                os.rename(log_file, backup_name)
                update_debug_log(f"Rotated log file: {log_file}")
        except Exception as e:
            print(f"Error rotating {log_file}: {e}")


def tail_log(log_type: str = "debug", lines: int = 50):
    """Get last N lines from log file"""
    log_files = {
        "debug": debug_log_path,
        "main": log_file_path,
        "conversation": "conversation.log",
        "error": "error.log"
    }
    
    log_file = log_files.get(log_type, debug_log_path)
    
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        return ""
    except Exception as e:
        return f"Error reading log: {e}"


# Initialize logging
update_debug_log("Z-Waif logging system initialized")
