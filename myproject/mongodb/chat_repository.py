import datetime
import logging
from .mongo import get_db, generate_uuid

logger = logging.getLogger(__name__)

def create_conversation(user_id, title="New Chat"):
    db = get_db()
    if db is None:
        return None

    conversation_id = generate_uuid()
    now = datetime.datetime.utcnow()
    
    doc = {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "conversation_type": "chatbot",
        "title": title,
        "status": "active",
        "created_at": now,
        "updated_at": now
    }
    
    try:
        db.conversations.insert_one(doc)
        return conversation_id
    except Exception as e:
        logger.error(f"MongoDB Error - create_conversation: {e}")
        return None

def save_message(conversation_id, user_id, sender, message_content, message_type="text", metadata=None):
    db = get_db()
    if db is None:
        return None

    now = datetime.datetime.utcnow()
    msg_id = generate_uuid()
    
    doc = {
        "message_id": msg_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "sender": sender,  # 'user' or 'assistant'
        "message": message_content,
        "message_type": message_type,
        "timestamp": now,
        "is_read": True,
        "metadata": metadata or {}
    }
    
    try:
        db.messages.insert_one(doc)
        db.conversations.update_one(
            {"conversation_id": conversation_id},
            {"$set": {"updated_at": now}}
        )
        return msg_id
    except Exception as e:
        logger.error(f"MongoDB Error - save_message: {e}")
        return None

def get_user_conversations(user_id):
    db = get_db()
    if db is None:
        return []
    
    try:
        cursor = db.conversations.find({"user_id": user_id, "conversation_type": "chatbot"}).sort("updated_at", -1)
        return list(cursor)
    except Exception as e:
        logger.error(f"MongoDB Error - get_user_conversations: {e}")
        return []

def get_conversation_messages(conversation_id):
    db = get_db()
    if db is None:
        return []
    
    try:
        cursor = db.messages.find({"conversation_id": conversation_id}).sort("timestamp", 1)
        return list(cursor)
    except Exception as e:
        logger.error(f"MongoDB Error - get_conversation_messages: {e}")
        return []

def delete_conversation(conversation_id, user_id):
    db = get_db()
    if db is None:
        return False
        
    try:
        db.conversations.delete_one({"conversation_id": conversation_id, "user_id": user_id})
        db.messages.delete_many({"conversation_id": conversation_id})
        return True
    except Exception as e:
        logger.error(f"MongoDB Error - delete_conversation: {e}")
        return False

def delete_all_user_conversations(user_id):
    db = get_db()
    if db is None:
        return False
        
    try:
        convs = db.conversations.find({"user_id": user_id})
        conv_ids = [c["conversation_id"] for c in convs]
        
        db.conversations.delete_many({"user_id": user_id})
        db.messages.delete_many({"conversation_id": {"$in": conv_ids}})
        return True
    except Exception as e:
        logger.error(f"MongoDB Error - delete_all_user_conversations: {e}")
        return False

def rename_conversation(conversation_id, user_id, new_title):
    db = get_db()
    if db is None:
        return False
        
    try:
        db.conversations.update_one(
            {"conversation_id": conversation_id, "user_id": user_id},
            {"$set": {"title": new_title, "updated_at": datetime.datetime.utcnow()}}
        )
        return True
    except Exception as e:
        logger.error(f"MongoDB Error - rename_conversation: {e}")
        return False

def search_conversations(user_id, query):
    db = get_db()
    if db is None:
        return []
        
    try:
        cursor = db.conversations.find(
            {"user_id": user_id, "$text": {"$search": query}}
        ).sort("updated_at", -1)
        return list(cursor)
    except Exception as e:
        logger.error(f"MongoDB Error - search_conversations: {e}")
        return []
