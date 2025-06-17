import time
import threading
import datetime
import json
import os
import utils.zw_logging
import utils.voice
import API.gemini_controller

# Alarm system variables
active_alarms = []
alarm_thread = None
is_alarm_system_running = False

def initialize():
    """Initialize alarm system"""
    global is_alarm_system_running, alarm_thread
    
    load_alarms()
    
    is_alarm_system_running = True
    alarm_thread = threading.Thread(target=alarm_monitoring_loop)
    alarm_thread.daemon = True
    alarm_thread.start()
    
    utils.zw_logging.update_debug_log("Alarm system initialized")


def alarm_monitoring_loop():
    """Main alarm monitoring loop"""
    while is_alarm_system_running:
        try:
            current_time = datetime.datetime.now()
            
            # Check each active alarm
            for alarm in active_alarms[:]:  # Copy list to avoid modification during iteration
                if should_trigger_alarm(alarm, current_time):
                    trigger_alarm(alarm)
                    
                    # Remove one-time alarms
                    if not alarm.get("recurring", False):
                        active_alarms.remove(alarm)
                        save_alarms()
            
            time.sleep(10)  # Check every 10 seconds
            
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Alarm monitoring error: {e}")
            time.sleep(30)


def should_trigger_alarm(alarm: dict, current_time: datetime.datetime) -> bool:
    """Check if alarm should be triggered"""
    try:
        alarm_time = datetime.datetime.strptime(alarm["time"], "%H:%M")
        current_time_only = current_time.replace(second=0, microsecond=0)
        alarm_time_today = current_time_only.replace(
            hour=alarm_time.hour,
            minute=alarm_time.minute
        )
        
        # Check if it's time for the alarm
        if current_time_only >= alarm_time_today:
            # Check if already triggered today
            last_triggered = alarm.get("last_triggered", "")
            today_str = current_time.strftime("%Y-%m-%d")
            
            if last_triggered != today_str:
                return True
        
        return False
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Alarm check error: {e}")
        return False


def trigger_alarm(alarm: dict):
    """Trigger a specific alarm"""
    try:
        alarm_name = alarm.get("name", "Unnamed Alarm")
        alarm_message = alarm.get("message", "Wake up! It's time!")
        
        utils.zw_logging.update_debug_log(f"Triggering alarm: {alarm_name}")
        
        # Mark as triggered today
        alarm["last_triggered"] = datetime.datetime.now().strftime("%Y-%m-%d")
        save_alarms()
        
        # Create wake-up message
        wake_up_prompt = f"It's time for your alarm '{alarm_name}'! {alarm_message} Please wake up the user in your characteristic style."
        
        # Send to AI for personalized wake-up message
        API.gemini_controller.send_message(wake_up_prompt)
        response = API.gemini_controller.get_last_response()
        
        # Speak the wake-up message
        utils.voice.speak_line(response, refuse_pause=True)
        
        utils.zw_logging.update_debug_log(f"Alarm '{alarm_name}' triggered successfully")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Alarm trigger error: {e}")


def add_alarm(name: str, time_str: str, message: str = "", recurring: bool = False):
    """Add a new alarm"""
    try:
        # Validate time format
        datetime.datetime.strptime(time_str, "%H:%M")
        
        new_alarm = {
            "name": name,
            "time": time_str,
            "message": message,
            "recurring": recurring,
            "enabled": True,
            "created": datetime.datetime.now().isoformat()
        }
        
        active_alarms.append(new_alarm)
        save_alarms()
        
        utils.zw_logging.update_debug_log(f"Alarm added: {name} at {time_str}")
        return True
        
    except ValueError:
        utils.zw_logging.update_debug_log(f"Invalid time format for alarm: {time_str}")
        return False
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error adding alarm: {e}")
        return False


def remove_alarm(alarm_name: str):
    """Remove an alarm by name"""
    global active_alarms
    
    try:
        active_alarms = [alarm for alarm in active_alarms if alarm.get("name") != alarm_name]
        save_alarms()
        utils.zw_logging.update_debug_log(f"Alarm removed: {alarm_name}")
        return True
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error removing alarm: {e}")
        return False


def get_active_alarms():
    """Get list of active alarms"""
    return active_alarms.copy()


def toggle_alarm(alarm_name: str):
    """Toggle alarm enabled/disabled state"""
    try:
        for alarm in active_alarms:
            if alarm.get("name") == alarm_name:
                alarm["enabled"] = not alarm.get("enabled", True)
                save_alarms()
                utils.zw_logging.update_debug_log(f"Alarm '{alarm_name}' {'enabled' if alarm['enabled'] else 'disabled'}")
                return alarm["enabled"]
        return None
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error toggling alarm: {e}")
        return None


def load_alarms():
    """Load alarms from file"""
    global active_alarms
    
    try:
        alarms_file = "Configurables/Alarms/alarms.json"
        
        if os.path.exists(alarms_file):
            with open(alarms_file, 'r', encoding='utf-8') as f:
                active_alarms = json.load(f)
        else:
            active_alarms = []
            
        utils.zw_logging.update_debug_log(f"Loaded {len(active_alarms)} alarms")
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error loading alarms: {e}")
        active_alarms = []


def save_alarms():
    """Save alarms to file"""
    try:
        alarms_file = "Configurables/Alarms/alarms.json"
        os.makedirs(os.path.dirname(alarms_file), exist_ok=True)
        
        with open(alarms_file, 'w', encoding='utf-8') as f:
            json.dump(active_alarms, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Error saving alarms: {e}")


def stop_alarm_system():
    """Stop the alarm system"""
    global is_alarm_system_running
    is_alarm_system_running = False
    utils.zw_logging.update_debug_log("Alarm system stopped")


# Initialize alarm system
initialize()
