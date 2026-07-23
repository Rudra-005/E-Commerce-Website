import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, PyMongoError
from django.conf import settings
import uuid

logger = logging.getLogger(__name__)

class MongoDBClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        try:
            import os
            # Assuming default URI if not in settings
            uri = getattr(settings, 'MONGODB_URI', os.getenv('MONGODB_URI', 'mongodb://localhost:27017'))
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            
            # Test connection
            self.client.admin.command('ping')
            
            self.db = self.client['shopkart']
            
            # Setup Collections
            self.conversations = self.db['conversations']
            self.messages = self.db['messages']
            self.support_conversations = self.db['support_conversations']
            self.support_messages = self.db['support_messages']
            
            # Setup Indexes
            self._setup_indexes()
            
            logger.info("Successfully connected to MongoDB and initialized indexes.")
            
        except ConnectionFailure as e:
            import os
            uri = getattr(settings, 'MONGODB_URI', os.getenv('MONGODB_URI', ''))
            safe_uri = uri.split('@')[-1] if '@' in uri else 'localhost'
            logger.error(f"Failed to connect to MongoDB at {safe_uri}. Real Error: {e}")
            self.client = None
            self.db = None
        except Exception as e:
            logger.error(f"Error initializing MongoDB: {e}")
            self.client = None
            self.db = None

    def _setup_indexes(self):
        if self.db is None:
            return
            
        # Chatbot Conversations
        self.conversations.create_index([("user_id", ASCENDING)])
        self.conversations.create_index([("conversation_id", ASCENDING)], unique=True)
        self.conversations.create_index([("updated_at", DESCENDING)])
        self.conversations.create_index([("title", "text")])
        
        # Chatbot Messages
        self.messages.create_index([("conversation_id", ASCENDING), ("timestamp", ASCENDING)])
        
        # Support Conversations
        self.support_conversations.create_index([("customer_id", ASCENDING)])
        self.support_conversations.create_index([("ticket_id", ASCENDING)], unique=True)
        self.support_conversations.create_index([("conversation_id", ASCENDING)], unique=True)
        
        # Support Messages
        self.support_messages.create_index([("conversation_id", ASCENDING), ("timestamp", ASCENDING)])

def get_db():
    return MongoDBClient().db

def generate_uuid():
    return str(uuid.uuid4())
