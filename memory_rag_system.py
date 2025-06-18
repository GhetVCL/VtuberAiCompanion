"""
Advanced Memory and RAG System for Z-Waif AI VTuber
Implements semantic search, long-term memory, and contextual understanding
"""

import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import re
from models import ConversationLog, Memory, UserProfile, KnowledgeBase, create_session
import google.generativeai as genai

class SimpleEmbedding:
    """Simple text embedding for semantic similarity without external dependencies"""
    
    def __init__(self):
        self.vocab = {}
        self.idf_scores = {}
    
    def _tokenize(self, text: str) -> List[str]:
        """Basic tokenization"""
        text = re.sub(r'[^\w\s]', '', text.lower())
        return text.split()
    
    def _build_vocab(self, texts: List[str]):
        """Build vocabulary from texts"""
        word_counts = {}
        doc_counts = {}
        
        for text in texts:
            tokens = self._tokenize(text)
            unique_tokens = set(tokens)
            
            for token in tokens:
                word_counts[token] = word_counts.get(token, 0) + 1
            
            for token in unique_tokens:
                doc_counts[token] = doc_counts.get(token, 0) + 1
        
        # Calculate IDF scores
        total_docs = len(texts)
        for word, doc_count in doc_counts.items():
            self.idf_scores[word] = np.log(total_docs / (1 + doc_count))
        
        self.vocab = {word: idx for idx, word in enumerate(word_counts.keys())}
    
    def embed_text(self, text: str, vocab_size: int = 100) -> List[float]:
        """Create embedding vector for text"""
        tokens = self._tokenize(text)
        
        # Create TF-IDF vector
        vector = [0.0] * min(vocab_size, len(self.vocab))
        token_counts = {}
        
        for token in tokens:
            token_counts[token] = token_counts.get(token, 0) + 1
        
        for token, count in token_counts.items():
            if token in self.vocab:
                idx = self.vocab[token]
                if idx < len(vector):
                    tf = count / len(tokens)
                    idf = self.idf_scores.get(token, 1.0)
                    vector[idx] = tf * idf
        
        # Normalize vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = [x / norm for x in vector]
        
        return vector
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between vectors"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = np.sqrt(sum(a * a for a in vec1))
        norm2 = np.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)

class MemoryRAGSystem:
    """Advanced Memory and RAG system"""
    
    def __init__(self):
        self.embedding_model = SimpleEmbedding()
        self.conversation_cache = []
        self.memory_cache = []
        self.similarity_threshold = 0.3
        self.max_context_length = 8000
        self.initialize_system()
    
    def initialize_system(self):
        """Initialize the memory and RAG system"""
        try:
            # Load existing conversations to build embedding vocabulary
            session = create_session()
            conversations = session.query(ConversationLog).limit(1000).all()
            
            if conversations:
                texts = []
                for conv in conversations:
                    texts.append(conv.user_message)
                    texts.append(conv.ai_response)
                
                self.embedding_model._build_vocab(texts)
                self.conversation_cache = conversations[-50:]  # Keep recent conversations
            
            # Load memories
            memories = session.query(Memory).limit(500).all()
            self.memory_cache = memories
            
            session.close()
            print("Memory and RAG system initialized")
            
        except Exception as e:
            print(f"Warning: Could not initialize memory system: {e}")
    
    def store_conversation(self, user_id: str, user_message: str, ai_response: str, 
                          platform: str = 'web', session_id: str = None) -> int:
        """Store conversation with embedding"""
        try:
            session = create_session()
            
            # Create embedding for user message
            embedding = self.embedding_model.embed_text(user_message + " " + ai_response)
            embedding_str = json.dumps(embedding)
            
            # Extract context data
            context_data = self._extract_context(user_message, ai_response)
            
            conversation = ConversationLog(
                user_id=user_id,
                user_message=user_message,
                ai_response=ai_response,
                platform=platform,
                context_data=context_data,
                embedding_vector=embedding_str,
                session_id=session_id
            )
            
            session.add(conversation)
            session.commit()
            
            conv_id = conversation.id
            session.close()
            
            # Update cache
            self.conversation_cache.append(conversation)
            if len(self.conversation_cache) > 50:
                self.conversation_cache = self.conversation_cache[-50:]
            
            # Extract and store memories
            self._extract_and_store_memories(user_id, user_message, ai_response, conv_id)
            
            return conv_id
            
        except Exception as e:
            print(f"Error storing conversation: {e}")
            return 0
    
    def _extract_context(self, user_message: str, ai_response: str) -> Dict[str, Any]:
        """Extract context information from conversation"""
        context = {
            'topics': [],
            'sentiment': 'neutral',
            'intent': 'chat',
            'entities': []
        }
        
        # Simple topic extraction
        topics = []
        message_lower = user_message.lower()
        
        # Topic keywords
        topic_keywords = {
            'technology': ['tech', 'computer', 'ai', 'programming', 'code', 'software'],
            'gaming': ['game', 'play', 'gaming', 'stream', 'twitch'],
            'music': ['music', 'song', 'sing', 'dance', 'melody'],
            'art': ['art', 'draw', 'paint', 'creative', 'design'],
            'personal': ['feel', 'think', 'like', 'love', 'hate', 'prefer']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                topics.append(topic)
        
        context['topics'] = topics
        
        # Simple sentiment analysis
        positive_words = ['good', 'great', 'awesome', 'love', 'like', 'happy', 'amazing']
        negative_words = ['bad', 'hate', 'sad', 'angry', 'terrible', 'awful', 'frustrated']
        
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        
        if positive_count > negative_count:
            context['sentiment'] = 'positive'
        elif negative_count > positive_count:
            context['sentiment'] = 'negative'
        
        return context
    
    def _extract_and_store_memories(self, user_id: str, user_message: str, 
                                   ai_response: str, conversation_id: int):
        """Extract and store important memories from conversation"""
        try:
            # Simple memory extraction based on patterns
            memories_to_store = []
            message_lower = user_message.lower()
            
            # Extract preferences
            preference_patterns = [
                r"i (love|like|enjoy|prefer|hate|dislike) (.+)",
                r"my favorite (.+) is (.+)",
                r"i'm (into|interested in) (.+)"
            ]
            
            for pattern in preference_patterns:
                matches = re.findall(pattern, message_lower)
                for match in matches:
                    if len(match) == 2:
                        sentiment = match[0]
                        subject = match[1].strip()
                        
                        memory_content = f"User {sentiment} {subject}"
                        memories_to_store.append({
                            'type': 'preference',
                            'content': memory_content,
                            'importance': 0.8 if sentiment in ['love', 'like', 'enjoy'] else 0.6
                        })
            
            # Extract facts about user
            fact_patterns = [
                r"i am (.+)",
                r"i work (.+)",
                r"i live (.+)",
                r"my name is (.+)"
            ]
            
            for pattern in fact_patterns:
                matches = re.findall(pattern, message_lower)
                for match in matches:
                    memory_content = f"User is/has {match.strip()}"
                    memories_to_store.append({
                        'type': 'fact',
                        'content': memory_content,
                        'importance': 0.9
                    })
            
            # Store memories in database
            session = create_session()
            
            for memory_data in memories_to_store:
                embedding = self.embedding_model.embed_text(memory_data['content'])
                
                memory = Memory(
                    user_id=user_id,
                    memory_type=memory_data['type'],
                    content=memory_data['content'],
                    importance_score=memory_data['importance'],
                    confidence_score=0.8,
                    embedding_vector=json.dumps(embedding),
                    conversation_id=conversation_id
                )
                
                session.add(memory)
                self.memory_cache.append(memory)
            
            session.commit()
            session.close()
            
        except Exception as e:
            print(f"Error extracting memories: {e}")
    
    def search_similar_conversations(self, query: str, user_id: str = None, 
                                   max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for similar conversations using semantic similarity"""
        try:
            query_embedding = self.embedding_model.embed_text(query)
            results = []
            
            session = create_session()
            conversations = session.query(ConversationLog)
            
            if user_id:
                conversations = conversations.filter(ConversationLog.user_id == user_id)
            
            conversations = conversations.order_by(ConversationLog.created_at.desc()).limit(100).all()
            
            for conv in conversations:
                if conv.embedding_vector:
                    try:
                        conv_embedding = json.loads(conv.embedding_vector)
                        similarity = self.embedding_model.cosine_similarity(query_embedding, conv_embedding)
                        
                        if similarity > self.similarity_threshold:
                            results.append({
                                'conversation': conv,
                                'similarity': similarity,
                                'user_message': conv.user_message,
                                'ai_response': conv.ai_response,
                                'created_at': conv.created_at
                            })
                    except:
                        continue
            
            session.close()
            
            # Sort by similarity and return top results
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results[:max_results]
            
        except Exception as e:
            print(f"Error searching conversations: {e}")
            return []
    
    def get_relevant_memories(self, query: str, user_id: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Get relevant memories for current context"""
        try:
            query_embedding = self.embedding_model.embed_text(query)
            results = []
            
            session = create_session()
            memories = session.query(Memory).filter(
                Memory.user_id == user_id
            ).order_by(Memory.importance_score.desc()).limit(50).all()
            
            for memory in memories:
                if memory.embedding_vector:
                    try:
                        memory_embedding = json.loads(memory.embedding_vector)
                        similarity = self.embedding_model.cosine_similarity(query_embedding, memory_embedding)
                        
                        if similarity > self.similarity_threshold:
                            # Update access count
                            memory.access_count += 1
                            memory.last_accessed = datetime.utcnow()
                            
                            results.append({
                                'memory': memory,
                                'similarity': similarity,
                                'content': memory.content,
                                'type': memory.memory_type,
                                'importance': memory.importance_score
                            })
                    except:
                        continue
            
            session.commit()
            session.close()
            
            # Sort by combined score (similarity + importance)
            for result in results:
                result['combined_score'] = (result['similarity'] * 0.7 + 
                                          result['importance'] * 0.3)
            
            results.sort(key=lambda x: x['combined_score'], reverse=True)
            return results[:max_results]
            
        except Exception as e:
            print(f"Error getting memories: {e}")
            return []
    
    def build_context_for_response(self, user_message: str, user_id: str) -> str:
        """Build enriched context for AI response"""
        context_parts = []
        
        # Get relevant memories
        memories = self.get_relevant_memories(user_message, user_id, max_results=3)
        if memories:
            memory_context = "Relevant memories about this user:\n"
            for mem in memories:
                memory_context += f"- {mem['content']} (confidence: {mem['memory']['confidence_score']:.1f})\n"
            context_parts.append(memory_context)
        
        # Get similar past conversations
        similar_convs = self.search_similar_conversations(user_message, user_id, max_results=2)
        if similar_convs:
            conv_context = "Similar past conversations:\n"
            for conv in similar_convs:
                conv_context += f"- User: {conv['user_message'][:100]}...\n"
                conv_context += f"  Response: {conv['ai_response'][:100]}...\n"
            context_parts.append(conv_context)
        
        # Get user profile
        try:
            session = create_session()
            profile = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if profile and profile.preferences:
                profile_context = f"User preferences: {json.dumps(profile.preferences)}\n"
                context_parts.append(profile_context)
            session.close()
        except:
            pass
        
        # Combine all context
        if context_parts:
            full_context = "CONTEXT FOR PERSONALIZED RESPONSE:\n" + "\n".join(context_parts) + "\n"
            
            # Ensure context doesn't exceed max length
            if len(full_context) > self.max_context_length:
                full_context = full_context[:self.max_context_length] + "...\n"
            
            return full_context
        
        return ""
    
    def update_user_profile(self, user_id: str, interaction_data: Dict[str, Any]):
        """Update user profile based on interaction"""
        try:
            session = create_session()
            
            profile = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if not profile:
                profile = UserProfile(
                    user_id=user_id,
                    preferences={},
                    personality_profile={},
                    conversation_style={},
                    interaction_history={}
                )
                session.add(profile)
            
            # Update preferences based on conversation
            if 'topics' in interaction_data:
                current_prefs = profile.preferences or {}
                topic_prefs = current_prefs.get('topics', {})
                
                for topic in interaction_data['topics']:
                    topic_prefs[topic] = topic_prefs.get(topic, 0) + 1
                
                current_prefs['topics'] = topic_prefs
                profile.preferences = current_prefs
            
            # Update interaction history
            history = profile.interaction_history or {}
            history['last_interaction'] = datetime.utcnow().isoformat()
            history['total_interactions'] = history.get('total_interactions', 0) + 1
            profile.interaction_history = history
            
            session.commit()
            session.close()
            
        except Exception as e:
            print(f"Error updating user profile: {e}")
    
    def get_conversation_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get conversation statistics"""
        try:
            session = create_session()
            
            # Total conversations
            query = session.query(ConversationLog)
            if user_id:
                query = query.filter(ConversationLog.user_id == user_id)
            
            total_conversations = query.count()
            
            # Recent activity (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_conversations = query.filter(
                ConversationLog.created_at >= week_ago
            ).count()
            
            # Memory count
            memory_query = session.query(Memory)
            if user_id:
                memory_query = memory_query.filter(Memory.user_id == user_id)
            
            total_memories = memory_query.count()
            
            session.close()
            
            return {
                'total_conversations': total_conversations,
                'recent_conversations': recent_conversations,
                'total_memories': total_memories,
                'system_status': 'active'
            }
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {'error': str(e)}

# Global instance
memory_rag_system = MemoryRAGSystem()