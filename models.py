"""
Database models for Z-Waif AI VTuber system
Advanced memory, RAG, and conversation tracking
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import os

Base = declarative_base()

class ConversationLog(Base):
    """Store all conversations with metadata"""
    __tablename__ = 'conversation_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), nullable=False)
    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    platform = Column(String(50), default='web')  # web, discord, minecraft
    context_data = Column(JSON)  # Additional context like emotions, topics
    embedding_vector = Column(Text)  # Serialized embedding for RAG
    created_at = Column(DateTime, server_default=func.now())
    session_id = Column(String(100))
    
    # Relationships
    memories = relationship("Memory", back_populates="conversation")

class Memory(Base):
    """Advanced memory system for long-term context"""
    __tablename__ = 'memories'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), nullable=False)
    memory_type = Column(String(50))  # fact, preference, relationship, event
    content = Column(Text, nullable=False)
    importance_score = Column(Float, default=1.0)
    confidence_score = Column(Float, default=1.0)
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime)
    tags = Column(JSON)  # Searchable tags
    embedding_vector = Column(Text)
    conversation_id = Column(Integer, ForeignKey('conversation_logs.id'))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    conversation = relationship("ConversationLog", back_populates="memories")

class UserProfile(Base):
    """User profiles and preferences"""
    __tablename__ = 'user_profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), unique=True, nullable=False)
    username = Column(String(100))
    platform = Column(String(50))
    preferences = Column(JSON)  # Communication style, topics of interest
    personality_profile = Column(JSON)  # Detected personality traits
    conversation_style = Column(JSON)  # Preferred response style
    interaction_history = Column(JSON)  # Summary of past interactions
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class EmotionalState(Base):
    """Track emotional context and responses"""
    __tablename__ = 'emotional_states'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), nullable=False)
    conversation_id = Column(Integer, ForeignKey('conversation_logs.id'))
    detected_emotion = Column(String(50))
    confidence = Column(Float)
    response_emotion = Column(String(50))
    context_factors = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())

class StreamingSession(Base):
    """Track streaming sessions and real-time interactions"""
    __tablename__ = 'streaming_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True, nullable=False)
    platform = Column(String(50))  # discord, twitch, youtube
    start_time = Column(DateTime, server_default=func.now())
    end_time = Column(DateTime)
    participants = Column(JSON)  # List of active users
    session_data = Column(JSON)  # Stream metadata
    is_active = Column(Boolean, default=True)

class KnowledgeBase(Base):
    """Structured knowledge for RAG system"""
    __tablename__ = 'knowledge_base'
    
    id = Column(Integer, primary_key=True)
    topic = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100))
    subcategory = Column(String(100))
    relevance_score = Column(Float, default=1.0)
    source = Column(String(200))
    embedding_vector = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# Database setup
def get_database_url():
    """Get database URL from environment"""
    return os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/zwaif')

def create_database_engine():
    """Create database engine"""
    return create_engine(get_database_url())

def create_session():
    """Create database session"""
    engine = create_database_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def init_database():
    """Initialize database tables"""
    engine = create_database_engine()
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

if __name__ == "__main__":
    init_database()