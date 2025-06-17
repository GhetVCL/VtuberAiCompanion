import threading
import time
import queue
import utils.zw_logging
import main

# Pipe management variables
main_pipe_running = False
active_pipes = {}
pipe_queue = queue.Queue()
pipe_manager_thread = None

def initialize():
    """Initialize the pipe management system"""
    global pipe_manager_thread
    
    pipe_manager_thread = threading.Thread(target=pipe_manager_loop)
    pipe_manager_thread.daemon = True
    pipe_manager_thread.start()
    
    utils.zw_logging.update_debug_log("Uni-pipes system initialized")


def pipe_manager_loop():
    """Main pipe manager loop"""
    while True:
        try:
            # Process queued pipes
            if not pipe_queue.empty():
                pipe_data = pipe_queue.get_nowait()
                execute_pipe(pipe_data)
            
            time.sleep(0.01)
            
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Pipe manager error: {e}")
            time.sleep(0.1)


def start_new_pipe(desired_process: str, is_main_pipe: bool = False):
    """Start a new pipe process"""
    global main_pipe_running
    
    if is_main_pipe:
        main_pipe_running = True
    
    pipe_data = {
        "process": desired_process,
        "is_main": is_main_pipe,
        "timestamp": time.time()
    }
    
    pipe_queue.put(pipe_data)
    utils.zw_logging.update_debug_log(f"New pipe started: {desired_process}")


def execute_pipe(pipe_data: str):
    """Execute a specific pipe process"""
    global main_pipe_running
    
    process = pipe_data["process"]
    is_main = pipe_data["is_main"]
    
    try:
        # Route to appropriate function based on process type
        if process == "Main-Chat":
            main.main_converse()
        
        elif process == "Main-Next":
            main.main_next()
        
        elif process == "Main-Redo":
            # Implement redo functionality
            main.main_next()  # For now, same as next
        
        elif process == "Main-Soft-Reset":
            # Implement soft reset
            utils.zw_logging.update_debug_log("Soft reset executed")
        
        elif process == "Main-Alarm":
            # Implement alarm functionality
            utils.zw_logging.update_debug_log("Alarm functionality triggered")
        
        elif process == "Main-View-Image":
            # Implement image viewing
            utils.zw_logging.update_debug_log("Image viewing triggered")
        
        elif process == "Main-Blank":
            # Implement blank/clear functionality
            utils.zw_logging.update_debug_log("Blank command executed")
        
        elif process == "Hangout-Loop":
            # Implement hangout mode
            utils.zw_logging.update_debug_log("Hangout mode activated")
        
        else:
            utils.zw_logging.update_debug_log(f"Unknown pipe process: {process}")
    
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Pipe execution error in {process}: {e}")
    
    finally:
        if is_main:
            main_pipe_running = False


def stop_main_pipe():
    """Stop the main pipe"""
    global main_pipe_running
    main_pipe_running = False


def get_pipe_status():
    """Get current pipe status"""
    return {
        "main_pipe_running": main_pipe_running,
        "active_pipes": len(active_pipes),
        "queued_pipes": pipe_queue.qsize()
    }


def clear_pipe_queue():
    """Clear all queued pipes"""
    while not pipe_queue.empty():
        try:
            pipe_queue.get_nowait()
        except queue.Empty:
            break
    
    utils.zw_logging.update_debug_log("Pipe queue cleared")


# Initialize on import
initialize()
