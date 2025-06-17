"""
Cane Library - Core utility functions for Z-Waif
Provides common helper functions and utilities used across the system
"""

import os
import re
import time
import json
import threading
from typing import List, Dict, Any, Optional, Union
import utils.zw_logging

# Global utility variables
temp_files = []
cleanup_thread = None
is_cleanup_running = False

def initialize():
    """Initialize the Cane Library"""
    global cleanup_thread, is_cleanup_running
    
    is_cleanup_running = True
    cleanup_thread = threading.Thread(target=cleanup_loop)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    utils.zw_logging.update_debug_log("Cane Library initialized")


def cleanup_loop():
    """Background cleanup loop for temporary files"""
    while is_cleanup_running:
        try:
            cleanup_temp_files()
            time.sleep(300)  # Cleanup every 5 minutes
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Cleanup loop error: {e}")
            time.sleep(60)


def cleanup_temp_files():
    """Clean up temporary files"""
    global temp_files
    
    cleaned_count = 0
    remaining_files = []
    
    for file_path in temp_files:
        try:
            if os.path.exists(file_path):
                # Check if file is older than 30 minutes
                file_age = time.time() - os.path.getmtime(file_path)
                if file_age > 1800:  # 30 minutes
                    os.remove(file_path)
                    cleaned_count += 1
                else:
                    remaining_files.append(file_path)
            else:
                # File already removed
                pass
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Error cleaning temp file {file_path}: {e}")
            remaining_files.append(file_path)
    
    temp_files = remaining_files
    
    if cleaned_count > 0:
        utils.zw_logging.update_debug_log(f"Cleaned up {cleaned_count} temporary files")


def register_temp_file(file_path: str):
    """Register a temporary file for cleanup"""
    global temp_files
    temp_files.append(file_path)


def clean_text(text: str) -> str:
    """Clean text for processing"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def remove_repeats(text: str, min_length: int = 3) -> str:
    """Remove repeated phrases from text"""
    if not text or len(text) < min_length * 2:
        return text
    
    words = text.split()
    if len(words) < 4:
        return text
    
    # Check for repeated segments at the end
    text_length = len(words)
    
    for segment_length in range(1, text_length // 2 + 1):
        # Get the last segment
        last_segment = words[-segment_length:]
        
        # Check if this segment is repeated before it
        if segment_length <= text_length - segment_length:
            prev_segment = words[-(segment_length * 2):-segment_length]
            
            if last_segment == prev_segment:
                # Found repetition, remove the last occurrence
                return ' '.join(words[:-segment_length])
    
    return text


def old_remove_repeats(text: str) -> str:
    """Legacy repeat removal function (kept for compatibility)"""
    if not text:
        return text
    
    # Split by punctuation and check for repeats
    sentences = re.split(r'[.!?]', text)
    
    if len(sentences) >= 2:
        # Check if last two sentences are similar
        if len(sentences) >= 2 and sentences[-1].strip() and sentences[-2].strip():
            if sentences[-1].strip().lower() == sentences[-2].strip().lower():
                # Remove the last repeated sentence
                text = '.'.join(sentences[:-1]) + '.'
    
    return text


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system use"""
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
    
    # Limit length
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    
    # Ensure it's not empty
    if not sanitized.strip():
        sanitized = "unnamed_file"
    
    return sanitized.strip()


def ensure_directory(dir_path: str) -> bool:
    """Ensure directory exists, create if necessary"""
    try:
        os.makedirs(dir_path, exist_ok=True)
        return True
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error creating directory {dir_path}: {e}")
        return False


def safe_json_load(file_path: str, default_value: Any = None) -> Any:
    """Safely load JSON file with fallback"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default_value
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error loading JSON from {file_path}: {e}")
        return default_value


def safe_json_save(file_path: str, data: Any) -> bool:
    """Safely save data to JSON file"""
    try:
        # Ensure directory exists
        ensure_directory(os.path.dirname(file_path))
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error saving JSON to {file_path}: {e}")
        return False


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length"""
    if not text or len(text) <= max_length:
        return text
    
    if max_length <= len(suffix):
        return text[:max_length]
    
    return text[:max_length - len(suffix)] + suffix


def extract_commands(text: str, command_prefix: str = "/") -> List[str]:
    """Extract commands from text"""
    if not text:
        return []
    
    # Pattern to match commands like /command/ or /command/arg/
    pattern = rf'{re.escape(command_prefix)}([^{re.escape(command_prefix)}]+){re.escape(command_prefix)}'
    matches = re.findall(pattern, text)
    
    return [match.strip() for match in matches if match.strip()]


def format_time_elapsed(seconds: float) -> str:
    """Format elapsed time in a human-readable way"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"


def is_valid_url(url: str) -> bool:
    """Check if string is a valid URL"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None


def count_words(text: str) -> int:
    """Count words in text"""
    if not text:
        return 0
    return len(text.split())


def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes"""
    try:
        if os.path.exists(file_path):
            size_bytes = os.path.getsize(file_path)
            return size_bytes / (1024 * 1024)
        return 0.0
    except Exception:
        return 0.0


def rate_limit_check(last_action_time: float, min_interval: float) -> bool:
    """Check if enough time has passed since last action"""
    current_time = time.time()
    return (current_time - last_action_time) >= min_interval


def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    if not text:
        return text
    
    # Characters that need escaping in markdown
    chars_to_escape = ['*', '_', '`', '[', ']', '(', ')', '#', '+', '-', '.', '!']
    
    for char in chars_to_escape:
        text = text.replace(char, f'\\{char}')
    
    return text


def get_system_info() -> Dict[str, Any]:
    """Get basic system information"""
    import platform
    import psutil
    
    try:
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "disk_free_gb": round(psutil.disk_usage('.').free / (1024**3), 2)
        }
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error getting system info: {e}")
        return {"error": str(e)}


def stop_cleanup():
    """Stop the cleanup system"""
    global is_cleanup_running
    is_cleanup_running = False


# Initialize on import
initialize()
