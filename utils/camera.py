"""
Camera/Vision System - Handles image capture and vision processing
Integrates with multimodal AI for image understanding
"""

import os
import cv2
import base64
import threading
import time
from typing import Optional, List, Dict, Any
import utils.zw_logging
import utils.cane_lib
import API.gemini_controller

# Camera variables
camera = None
is_camera_active = False
last_capture_time = 0
capture_thread = None
latest_image_path = None

def initialize():
    """Initialize camera system"""
    global camera
    
    camera_enabled = os.getenv("CAMERA_ENABLED", "false").lower() == "true"
    
    if not camera_enabled:
        utils.zw_logging.update_debug_log("Camera system disabled in settings")
        return
    
    try:
        # Try to initialize camera
        camera = cv2.VideoCapture(0)
        
        if camera.isOpened():
            # Set camera properties
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            camera.set(cv2.CAP_PROP_FPS, 30)
            
            utils.zw_logging.update_debug_log("Camera system initialized successfully")
        else:
            camera = None
            utils.zw_logging.update_debug_log("Camera not available")
            
    except Exception as e:
        camera = None
        utils.zw_logging.update_debug_log(f"Camera initialization failed: {e}")


def capture_image(save_path: str = None) -> Optional[str]:
    """Capture image from camera"""
    global last_capture_time, latest_image_path
    
    if not camera or not camera.isOpened():
        utils.zw_logging.update_debug_log("Camera not available for capture")
        return None
    
    try:
        # Read frame from camera
        ret, frame = camera.read()
        
        if not ret:
            utils.zw_logging.update_debug_log("Failed to capture frame")
            return None
        
        # Generate filename if not provided
        if save_path is None:
            timestamp = int(time.time())
            save_path = f"temp_capture_{timestamp}.jpg"
            utils.cane_lib.register_temp_file(save_path)
        
        # Save image
        success = cv2.imwrite(save_path, frame)
        
        if success:
            last_capture_time = time.time()
            latest_image_path = save_path
            utils.zw_logging.update_debug_log(f"Image captured: {save_path}")
            return save_path
        else:
            utils.zw_logging.update_debug_log("Failed to save captured image")
            return None
            
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Image capture error: {e}")
        return None


def process_image_with_ai(image_path: str, user_prompt: str = "") -> str:
    """Process captured image with AI vision"""
    if not os.path.exists(image_path):
        return "Image file not found."
    
    try:
        # Convert image to base64 for API
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode()
        
        # Create vision prompt
        if not user_prompt:
            user_prompt = "What do you see in this image? Describe it in your characteristic style."
        
        vision_prompt = f"[Looking at image] {user_prompt}"
        
        # Send to Gemini with image context (placeholder - would need Gemini Vision API)
        # For now, simulate vision response
        vision_response = f"I can see an image that was just captured! {user_prompt}. Unfortunately, I need proper vision model integration to describe what I'm actually seeing."
        
        utils.zw_logging.update_debug_log(f"Processed image with AI: {len(vision_response)} characters")
        return vision_response
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"AI image processing error: {e}")
        return "I had trouble processing that image. Could you try again?"


def take_and_analyze_photo(user_prompt: str = "") -> str:
    """Capture and analyze photo in one operation"""
    image_path = capture_image()
    
    if not image_path:
        return "I couldn't take a photo right now. Is the camera available?"
    
    try:
        response = process_image_with_ai(image_path, user_prompt)
        return response
        
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Photo analysis error: {e}")
        return "I took a photo but had trouble analyzing it."


def start_camera_monitoring():
    """Start background camera monitoring"""
    global is_camera_active, capture_thread
    
    if not camera or is_camera_active:
        return
    
    is_camera_active = True
    capture_thread = threading.Thread(target=camera_monitoring_loop)
    capture_thread.daemon = True
    capture_thread.start()
    
    utils.zw_logging.update_debug_log("Camera monitoring started")


def camera_monitoring_loop():
    """Background camera monitoring loop"""
    while is_camera_active and camera and camera.isOpened():
        try:
            # Keep camera active and ready
            ret, frame = camera.read()
            
            if not ret:
                utils.zw_logging.update_debug_log("Camera monitoring: failed to read frame")
                time.sleep(1)
                continue
            
            # Small delay to prevent excessive CPU usage
            time.sleep(0.1)
            
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Camera monitoring error: {e}")
            time.sleep(1)


def stop_camera_monitoring():
    """Stop camera monitoring"""
    global is_camera_active
    is_camera_active = False


def get_camera_status() -> Dict[str, Any]:
    """Get camera system status"""
    return {
        "available": camera is not None and camera.isOpened() if camera else False,
        "active": is_camera_active,
        "last_capture": last_capture_time,
        "latest_image": latest_image_path
    }


def list_available_cameras() -> List[int]:
    """List available camera indices"""
    available_cameras = []
    
    # Test first 5 camera indices
    for i in range(5):
        try:
            test_camera = cv2.VideoCapture(i)
            if test_camera.isOpened():
                available_cameras.append(i)
            test_camera.release()
        except Exception:
            pass
    
    return available_cameras


def switch_camera(camera_index: int) -> bool:
    """Switch to different camera"""
    global camera
    
    try:
        # Release current camera
        if camera:
            camera.release()
        
        # Initialize new camera
        camera = cv2.VideoCapture(camera_index)
        
        if camera.isOpened():
            # Set camera properties
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            camera.set(cv2.CAP_PROP_FPS, 30)
            
            utils.zw_logging.update_debug_log(f"Switched to camera {camera_index}")
            return True
        else:
            camera = None
            utils.zw_logging.update_debug_log(f"Failed to switch to camera {camera_index}")
            return False
            
    except Exception as e:
        utils.zw_logging.update_debug_log(f"Camera switch error: {e}")
        camera = None
        return False


def cleanup_camera():
    """Clean up camera resources"""
    global camera, is_camera_active
    
    is_camera_active = False
    
    if camera:
        try:
            camera.release()
            utils.zw_logging.update_debug_log("Camera resources cleaned up")
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Camera cleanup error: {e}")
        finally:
            camera = None


def save_screenshot(filename: str = None) -> Optional[str]:
    """Save a screenshot of current camera view"""
    if filename is None:
        timestamp = int(time.time())
        filename = f"screenshot_{timestamp}.jpg"
    
    image_path = capture_image(filename)
    
    if image_path:
        utils.zw_logging.update_debug_log(f"Screenshot saved: {filename}")
    
    return image_path


# Initialize camera on import
initialize()
