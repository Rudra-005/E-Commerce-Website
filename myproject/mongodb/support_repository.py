import datetime
import logging
from .mongo import get_db, generate_uuid

logger = logging.getLogger(__name__)

def save_support_ticket(ticket_id, customer_id, title="Support Request"):
    db = get_db()
    if db is None:
        return None

    now = datetime.datetime.utcnow()
    
    doc = {
        "ticket_id": str(ticket_id),
        "conversation_id": str(ticket_id),  # Use ticket_id as conversation_id for simplicity
        "customer_id": customer_id,
        "conversation_type": "support",
        "title": title,
        "status": "open",
        "priority": "normal",
        "created_at": now,
        "updated_at": now,
        "resolved_at": None,
        "last_activity": now,
        "warning_sent": False,
        "warning_sent_at": None,
        "closed_at": None
    }
    
    try:
        # Upsert
        db.support_conversations.update_one(
            {"ticket_id": str(ticket_id)},
            {"$setOnInsert": doc},
            upsert=True
        )
        return str(ticket_id)
    except Exception as e:
        logger.error(f"MongoDB Error - save_support_ticket: {e}")
        return None

def save_support_message(ticket_id, sender_id, sender_type, message_content, is_system=False, message_type="text"):
    db = get_db()
    if db is None:
        return None

    now = datetime.datetime.utcnow()
    msg_id = generate_uuid()
    
    doc = {
        "message_id": msg_id,
        "conversation_id": str(ticket_id),
        "sender_id": sender_id,
        "sender_type": sender_type,  # 'customer' or 'admin'
        "message": message_content,
        "message_type": message_type,
        "timestamp": now,
        "is_read": False,
        "is_system": is_system,
        "metadata": {}
    }
    
    try:
        db.support_messages.insert_one(doc)
        
        status = "closed" if is_system else ("open" if sender_type == "customer" else "pending")
        
        update_fields = {
            "updated_at": now, 
            "status": status,
            "last_activity": now,
            "warning_sent": False,
            "warning_sent_at": None
        }
        
        db.support_conversations.update_one(
            {"ticket_id": str(ticket_id)},
            {"$set": update_fields}
        )
        return msg_id
    except Exception as e:
        logger.error(f"MongoDB Error - save_support_message: {e}")
        return None

def get_all_support_tickets():
    db = get_db()
    if db is None:
        return []
    try:
        cursor = db.support_conversations.find().sort("updated_at", -1)
        return list(cursor)
    except Exception as e:
        logger.error(f"MongoDB Error - get_all_support_tickets: {e}")
        return []

def get_support_messages(ticket_id):
    db = get_db()
    if db is None:
        return []
    try:
        cursor = db.support_messages.find({"conversation_id": str(ticket_id)}).sort("timestamp", 1)
        return list(cursor)
    except Exception as e:
        logger.error(f"MongoDB Error - get_support_messages: {e}")
        return []

def search_support_tickets(query):
    db = get_db()
    if db is None:
        return []
    try:
        # Text search if index is on title, else regex
        cursor = db.support_conversations.find({
            "$or": [
                {"ticket_id": {"$regex": query, "$options": "i"}},
                {"title": {"$regex": query, "$options": "i"}}
            ]
        }).sort("updated_at", -1)
        return list(cursor)
    except Exception as e:
        logger.error(f"MongoDB Error - search_support_tickets: {e}")
        return []

def get_idle_support_tickets(idle_seconds):
    db = get_db()
    if db is None:
        return []
        
    threshold = datetime.datetime.utcnow() - datetime.timedelta(seconds=idle_seconds)
    try:
        cursor = db.support_conversations.find({
            "status": {"$in": ["open", "pending"]},
            "warning_sent": False,
            "last_activity": {"$lt": threshold}
        })
        return list(cursor)
    except Exception as e:
        logger.error(f"MongoDB Error - get_idle_support_tickets: {e}")
        return []

def get_warned_support_tickets(warn_seconds):
    db = get_db()
    if db is None:
        return []
        
    threshold = datetime.datetime.utcnow() - datetime.timedelta(seconds=warn_seconds)
    try:
        cursor = db.support_conversations.find({
            "status": {"$in": ["open", "pending"]},
            "warning_sent": True,
            "warning_sent_at": {"$lt": threshold}
        })
        return list(cursor)
    except Exception as e:
        logger.error(f"MongoDB Error - get_warned_support_tickets: {e}")
        return []

def mark_warning_sent(ticket_id):
    db = get_db()
    if db is None:
        return False
        
    now = datetime.datetime.utcnow()
    try:
        db.support_conversations.update_one(
            {"ticket_id": str(ticket_id)},
            {"$set": {"warning_sent": True, "warning_sent_at": now}}
        )
        return True
    except Exception as e:
        logger.error(f"MongoDB Error - mark_warning_sent: {e}")
        return False

def reset_idle_status(ticket_id):
    db = get_db()
    if db is None:
        return False
        
    now = datetime.datetime.utcnow()
    try:
        db.support_conversations.update_one(
            {"ticket_id": str(ticket_id)},
            {"$set": {"warning_sent": False, "warning_sent_at": None, "last_activity": now}}
        )
        return True
    except Exception as e:
        logger.error(f"MongoDB Error - reset_idle_status: {e}")
        return False

def close_support_ticket(ticket_id):
    db = get_db()
    if db is None:
        return False
        
    now = datetime.datetime.utcnow()
    try:
        db.support_conversations.update_one(
            {"ticket_id": str(ticket_id)},
            {"$set": {"status": "closed", "closed_at": now}}
        )
        return True
    except Exception as e:
        logger.error(f"MongoDB Error - close_support_ticket: {e}")
        return False

