import json
import os
import re
from datetime import datetime
import utils.zw_logging

def convert_old_logs_to_new_format():
    """Convert old log formats to new JSON format"""
    try:
        # Look for various old log formats
        old_log_files = [
            "chat_history.txt",
            "conversation.log", 
            "old_chat.log",
            "backup.log"
        ]
        
        converted_entries = []
        
        for log_file in old_log_files:
            if os.path.exists(log_file):
                entries = parse_old_log_file(log_file)
                converted_entries.extend(entries)
        
        if converted_entries:
            # Merge with existing LiveLog.json
            existing_log = load_existing_live_log()
            all_entries = existing_log + converted_entries
            
            # Remove duplicates and sort by timestamp
            unique_entries = remove_duplicate_entries(all_entries)
            
            # Save to LiveLog.json
            save_live_log(unique_entries)
            
            utils.zw_logging.update_debug_log(f"Converted {len(converted_entries)} old log entries")
            return True
        
        return False
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Log conversion error: {e}")
        return False


def parse_old_log_file(file_path: str) -> list:
    """Parse various old log file formats"""
    entries = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try different parsing methods based on content
        if "User:" in content and "AI:" in content:
            entries = parse_user_ai_format(content)
        elif "You:" in content and "Assistant:" in content:
            entries = parse_you_assistant_format(content)
        elif "[" in content and "]" in content:
            entries = parse_bracketed_format(content)
        else:
            # Try simple line-by-line parsing
            entries = parse_simple_format(content)
        
        utils.zw_logging.update_debug_log(f"Parsed {len(entries)} entries from {file_path}")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error parsing {file_path}: {e}")
    
    return entries


def parse_user_ai_format(content: str) -> list:
    """Parse User:/AI: format logs"""
    entries = []
    lines = content.split('\n')
    
    current_user = ""
    current_ai = ""
    
    for line in lines:
        line = line.strip()
        if line.startswith("User:"):
            if current_user and current_ai:
                entries.append([current_user, current_ai])
            current_user = line[5:].strip()
            current_ai = ""
        elif line.startswith("AI:"):
            current_ai = line[3:].strip()
        elif current_ai and line:
            current_ai += " " + line
    
    # Add final entry
    if current_user and current_ai:
        entries.append([current_user, current_ai])
    
    return entries


def parse_you_assistant_format(content: str) -> list:
    """Parse You:/Assistant: format logs"""
    entries = []
    lines = content.split('\n')
    
    current_user = ""
    current_ai = ""
    
    for line in lines:
        line = line.strip()
        if line.startswith("You:"):
            if current_user and current_ai:
                entries.append([current_user, current_ai])
            current_user = line[4:].strip()
            current_ai = ""
        elif line.startswith("Assistant:"):
            current_ai = line[10:].strip()
        elif current_ai and line:
            current_ai += " " + line
    
    # Add final entry
    if current_user and current_ai:
        entries.append([current_user, current_ai])
    
    return entries


def parse_bracketed_format(content: str) -> list:
    """Parse [timestamp] format logs"""
    entries = []
    
    # Use regex to find conversation blocks
    pattern = r'\[(.*?)\].*?User:?\s*(.*?)(?:AI|Assistant):?\s*(.*?)(?=\[|$)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for match in matches:
        user_text = match[1].strip()
        ai_text = match[2].strip()
        
        if user_text and ai_text:
            entries.append([user_text, ai_text])
    
    return entries


def parse_simple_format(content: str) -> list:
    """Parse simple alternating line format"""
    entries = []
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    # Assume alternating user/AI lines
    for i in range(0, len(lines) - 1, 2):
        user_line = lines[i]
        ai_line = lines[i + 1] if i + 1 < len(lines) else ""
        
        if user_line and ai_line:
            entries.append([user_line, ai_line])
    
    return entries


def load_existing_live_log() -> list:
    """Load existing LiveLog.json"""
    try:
        if os.path.exists('LiveLog.json'):
            with open('LiveLog.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error loading existing log: {e}")
        return []


def remove_duplicate_entries(entries: list) -> list:
    """Remove duplicate conversation entries"""
    seen = set()
    unique_entries = []
    
    for entry in entries:
        if len(entry) >= 2:
            # Create a hash of the conversation
            entry_hash = hash((entry[0].strip().lower(), entry[1].strip().lower()))
            
            if entry_hash not in seen:
                seen.add(entry_hash)
                unique_entries.append(entry)
    
    return unique_entries


def save_live_log(entries: list):
    """Save entries to LiveLog.json"""
    try:
        with open('LiveLog.json', 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        
        # Also create backup
        backup_entries = entries[-50:] if len(entries) > 50 else entries
        with open('LiveLogBlank.json', 'w', encoding='utf-8') as f:
            json.dump(backup_entries, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error saving live log: {e}")


def backup_current_logs():
    """Create backup of current logs"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Backup LiveLog.json
        if os.path.exists('LiveLog.json'):
            backup_name = f'LiveLog_backup_{timestamp}.json'
            with open('LiveLog.json', 'r', encoding='utf-8') as source:
                with open(backup_name, 'w', encoding='utf-8') as backup:
                    backup.write(source.read())
        
        utils.zw_logging.update_debug_log(f"Logs backed up with timestamp: {timestamp}")
        return True
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Backup error: {e}")
        return False


def get_log_statistics():
    """Get statistics about current logs"""
    try:
        stats = {
            "total_conversations": 0,
            "total_user_messages": 0,
            "total_ai_messages": 0,
            "log_file_size": 0
        }
        
        if os.path.exists('LiveLog.json'):
            with open('LiveLog.json', 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            stats["total_conversations"] = len(log_data)
            stats["total_user_messages"] = len([entry for entry in log_data if len(entry) > 0])
            stats["total_ai_messages"] = len([entry for entry in log_data if len(entry) > 1])
            stats["log_file_size"] = os.path.getsize('LiveLog.json')
        
        return stats
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error getting log statistics: {e}")
        return {}
