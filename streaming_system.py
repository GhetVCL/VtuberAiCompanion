"""
Real-time Streaming System for Z-Waif AI VTuber
Handles WebSocket connections, real-time responses, and streaming features
"""

import asyncio
import websockets
import json
import uuid
from typing import Dict, List, Set, Any, Optional
from datetime import datetime
import threading
import queue
import time
from models import StreamingSession, create_session
from memory_rag_system import memory_rag_system

class StreamingManager:
    """Manages real-time streaming connections and responses"""
    
    def __init__(self):
        self.active_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.message_queue = queue.Queue()
        self.is_running = False
        self.server = None
        self.host = "0.0.0.0"
        self.port = 8765
        
    async def register_connection(self, websocket: websockets.WebSocketServerProtocol, user_id: str):
        """Register a new WebSocket connection"""
        session_id = str(uuid.uuid4())
        self.active_connections[session_id] = websocket
        self.user_sessions[user_id] = session_id
        
        # Store session in database
        try:
            db_session = create_session()
            streaming_session = StreamingSession(
                session_id=session_id,
                platform='websocket',
                participants=[user_id],
                session_data={'user_id': user_id, 'connected_at': datetime.utcnow().isoformat()}
            )
            db_session.add(streaming_session)
            db_session.commit()
            db_session.close()
        except Exception as e:
            print(f"Error storing streaming session: {e}")
        
        print(f"User {user_id} connected with session {session_id}")
        return session_id
    
    async def unregister_connection(self, session_id: str):
        """Unregister a WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        
        # Remove from user sessions
        user_to_remove = None
        for user_id, sess_id in self.user_sessions.items():
            if sess_id == session_id:
                user_to_remove = user_id
                break
        
        if user_to_remove:
            del self.user_sessions[user_to_remove]
        
        # Update database
        try:
            db_session = create_session()
            streaming_session = db_session.query(StreamingSession).filter(
                StreamingSession.session_id == session_id
            ).first()
            if streaming_session:
                streaming_session.end_time = datetime.utcnow()
                streaming_session.is_active = False
                db_session.commit()
            db_session.close()
        except Exception as e:
            print(f"Error updating streaming session: {e}")
        
        print(f"Session {session_id} disconnected")
    
    async def handle_message(self, websocket: websockets.WebSocketServerProtocol, 
                           session_id: str, message_data: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        try:
            message_type = message_data.get('type', 'chat')
            user_id = message_data.get('user_id', 'anonymous')
            content = message_data.get('content', '')
            
            if message_type == 'chat':
                # Process chat message with streaming response
                await self.handle_chat_message(websocket, session_id, user_id, content)
            
            elif message_type == 'typing':
                # Broadcast typing indicator to other users
                await self.broadcast_typing_indicator(user_id, session_id)
            
            elif message_type == 'heartbeat':
                # Respond to heartbeat
                await websocket.send(json.dumps({
                    'type': 'heartbeat_response',
                    'timestamp': datetime.utcnow().isoformat()
                }))
            
        except Exception as e:
            print(f"Error handling message: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Error processing message'
            }))
    
    async def handle_chat_message(self, websocket: websockets.WebSocketServerProtocol,
                                session_id: str, user_id: str, message: str):
        """Handle chat message with streaming response"""
        try:
            # Send acknowledgment
            await websocket.send(json.dumps({
                'type': 'message_received',
                'timestamp': datetime.utcnow().isoformat()
            }))
            
            # Get enhanced context from memory system
            context = memory_rag_system.build_context_for_response(message, user_id)
            
            # Import Gemini controller
            import google.generativeai as genai
            
            # Build enhanced prompt with context
            enhanced_prompt = f"""
{context}

Current message: {message}

Respond as Aria, the AI VTuber, using the context above to provide a personalized response.
Keep the response conversational and engaging, and reference relevant memories when appropriate.
"""
            
            # Start streaming response
            await websocket.send(json.dumps({
                'type': 'response_start',
                'timestamp': datetime.utcnow().isoformat()
            }))
            
            # Simulate streaming response (replace with actual Gemini streaming)
            response_text = await self.generate_streaming_response(enhanced_prompt, websocket)
            
            # Store conversation in memory system
            conv_id = memory_rag_system.store_conversation(
                user_id=user_id,
                user_message=message,
                ai_response=response_text,
                platform='websocket',
                session_id=session_id
            )
            
            # Update user profile
            context_data = memory_rag_system._extract_context(message, response_text)
            memory_rag_system.update_user_profile(user_id, context_data)
            
            # Send completion signal
            await websocket.send(json.dumps({
                'type': 'response_complete',
                'conversation_id': conv_id,
                'timestamp': datetime.utcnow().isoformat()
            }))
            
        except Exception as e:
            print(f"Error in chat handling: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Error generating response'
            }))
    
    async def generate_streaming_response(self, prompt: str, websocket: websockets.WebSocketServerProtocol) -> str:
        """Generate streaming response using Gemini"""
        try:
            # Initialize Gemini model
            model = genai.GenerativeModel("gemini-2.0-flash-exp")
            
            # Generate response
            response = model.generate_content(prompt)
            full_response = response.text
            
            # Simulate streaming by sending chunks
            words = full_response.split()
            current_chunk = ""
            
            for i, word in enumerate(words):
                current_chunk += word + " "
                
                # Send chunk every 3-5 words
                if (i + 1) % 4 == 0 or i == len(words) - 1:
                    await websocket.send(json.dumps({
                        'type': 'response_chunk',
                        'content': current_chunk.strip(),
                        'is_final': i == len(words) - 1
                    }))
                    current_chunk = ""
                    await asyncio.sleep(0.1)  # Small delay for streaming effect
            
            return full_response
            
        except Exception as e:
            print(f"Error generating response: {e}")
            error_response = "I'm having trouble generating a response right now. Please try again."
            
            await websocket.send(json.dumps({
                'type': 'response_chunk',
                'content': error_response,
                'is_final': True
            }))
            
            return error_response
    
    async def broadcast_typing_indicator(self, typing_user_id: str, exclude_session: str):
        """Broadcast typing indicator to other users"""
        typing_message = {
            'type': 'user_typing',
            'user_id': typing_user_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        for session_id, websocket in self.active_connections.items():
            if session_id != exclude_session:
                try:
                    await websocket.send(json.dumps(typing_message))
                except:
                    pass  # Connection might be closed
    
    async def broadcast_to_all(self, message: Dict[str, Any], exclude_session: str = None):
        """Broadcast message to all connected users"""
        message_str = json.dumps(message)
        
        for session_id, websocket in self.active_connections.items():
            if session_id != exclude_session:
                try:
                    await websocket.send(message_str)
                except:
                    pass
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle individual client connection"""
        session_id = None
        try:
            # Wait for initial connection message
            initial_message = await websocket.recv()
            data = json.loads(initial_message)
            
            if data.get('type') == 'connect':
                user_id = data.get('user_id', f'user_{uuid.uuid4().hex[:8]}')
                session_id = await self.register_connection(websocket, user_id)
                
                # Send connection confirmation
                await websocket.send(json.dumps({
                    'type': 'connected',
                    'session_id': session_id,
                    'user_id': user_id,
                    'timestamp': datetime.utcnow().isoformat()
                }))
                
                # Handle subsequent messages
                async for message in websocket:
                    try:
                        message_data = json.loads(message)
                        await self.handle_message(websocket, session_id, message_data)
                    except json.JSONDecodeError:
                        await websocket.send(json.dumps({
                            'type': 'error',
                            'message': 'Invalid JSON format'
                        }))
            
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            if session_id:
                await self.unregister_connection(session_id)
    
    async def start_server(self):
        """Start the WebSocket server"""
        try:
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10
            )
            self.is_running = True
            print(f"Streaming server started on ws://{self.host}:{self.port}")
            
            # Keep server running
            await self.server.wait_closed()
            
        except Exception as e:
            print(f"Error starting streaming server: {e}")
    
    def start_background_server(self):
        """Start server in background thread"""
        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start_server())
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        print("Streaming server started in background")
    
    def stop_server(self):
        """Stop the WebSocket server"""
        if self.server:
            self.server.close()
            self.is_running = False
            print("Streaming server stopped")
    
    def get_active_sessions(self) -> Dict[str, Any]:
        """Get information about active sessions"""
        return {
            'total_connections': len(self.active_connections),
            'active_users': len(self.user_sessions),
            'sessions': list(self.active_connections.keys())
        }

class RealtimeFeatures:
    """Additional real-time features for enhanced interaction"""
    
    def __init__(self, streaming_manager: StreamingManager):
        self.streaming_manager = streaming_manager
        self.emotion_detector = EmotionDetector()
        self.response_enhancer = ResponseEnhancer()
    
    async def process_with_emotion(self, message: str, user_id: str) -> Dict[str, Any]:
        """Process message with emotion detection"""
        emotion_data = self.emotion_detector.detect_emotion(message)
        
        # Store emotional context
        try:
            from models import EmotionalState
            db_session = create_session()
            
            emotion_state = EmotionalState(
                user_id=user_id,
                detected_emotion=emotion_data['emotion'],
                confidence=emotion_data['confidence'],
                context_factors=emotion_data
            )
            
            db_session.add(emotion_state)
            db_session.commit()
            db_session.close()
            
        except Exception as e:
            print(f"Error storing emotion data: {e}")
        
        return emotion_data

class EmotionDetector:
    """Simple emotion detection system"""
    
    def __init__(self):
        self.emotion_keywords = {
            'happy': ['happy', 'joy', 'excited', 'great', 'awesome', 'love', 'amazing'],
            'sad': ['sad', 'depressed', 'down', 'upset', 'crying', 'hurt'],
            'angry': ['angry', 'mad', 'furious', 'annoyed', 'frustrated', 'hate'],
            'anxious': ['worried', 'anxious', 'nervous', 'scared', 'afraid'],
            'surprised': ['wow', 'omg', 'surprised', 'shocked', 'amazing'],
            'neutral': []
        }
    
    def detect_emotion(self, text: str) -> Dict[str, Any]:
        """Detect emotion from text"""
        text_lower = text.lower()
        emotion_scores = {}
        
        for emotion, keywords in self.emotion_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                emotion_scores[emotion] = score
        
        if emotion_scores:
            detected_emotion = max(emotion_scores.keys(), key=lambda x: emotion_scores[x])
            confidence = emotion_scores[detected_emotion] / len(text.split())
        else:
            detected_emotion = 'neutral'
            confidence = 0.5
        
        return {
            'emotion': detected_emotion,
            'confidence': min(confidence, 1.0),
            'all_scores': emotion_scores
        }

class ResponseEnhancer:
    """Enhance responses based on context and emotion"""
    
    def __init__(self):
        self.personality_modifiers = {
            'happy': "I'm so glad to hear that! ",
            'sad': "I'm sorry you're feeling that way. ",
            'angry': "I understand you're frustrated. ",
            'anxious': "It's okay to feel worried sometimes. ",
            'surprised': "That's quite surprising! "
        }
    
    def enhance_response(self, base_response: str, emotion_data: Dict[str, Any]) -> str:
        """Enhance response based on detected emotion"""
        emotion = emotion_data.get('emotion', 'neutral')
        
        if emotion in self.personality_modifiers and emotion_data.get('confidence', 0) > 0.3:
            modifier = self.personality_modifiers[emotion]
            return modifier + base_response
        
        return base_response

# Global streaming manager instance
streaming_manager = StreamingManager()