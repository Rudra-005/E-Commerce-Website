import logging
import asyncio
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

# To prevent double start in dev server with auto-reloader
_scheduler = None

def check_idle_conversations():
    try:
        from mongodb.support_repository import (
            get_idle_support_tickets, 
            mark_warning_sent,
            get_warned_support_tickets,
            close_support_ticket,
            save_support_message
        )
        from shop.models import SupportConversation, SupportMessage

        channel_layer = get_channel_layer()

        # 1. Check for idle tickets (>30s)
        idle_tickets = get_idle_support_tickets(idle_seconds=30)
        for ticket in idle_tickets:
            ticket_id = ticket["ticket_id"]
            
            # Send warning
            warning_msg = (
                "Do you want to terminate the session?"
            )
            
            room_name = f'conversation_{ticket_id}'
            
            # Broadcast the warning event to both customer and admin
            async_to_sync(channel_layer.group_send)(
                room_name,
                {
                    'type': 'idle_warning',
                    'conversation_id': ticket_id,
                    'message': warning_msg
                }
            )
            
            # Mark as warning sent in MongoDB
            mark_warning_sent(ticket_id)
            logger.info(f"Sent idle warning for ticket {ticket_id}")

        # 2. Check for warned tickets that didn't respond (>60s since warning)
        warned_tickets = get_warned_support_tickets(warn_seconds=60)
        for ticket in warned_tickets:
            ticket_id = ticket["ticket_id"]
            
            # Close the ticket in MongoDB
            close_support_ticket(ticket_id)
            
            system_message = "This conversation has been automatically closed due to inactivity."
            
            # Save system message in MongoDB
            msg_id = save_support_message(
                ticket_id=ticket_id,
                sender_id="system",
                sender_type="system",
                message_content=system_message,
                is_system=True
            )
            
            # Close in PostgreSQL
            try:
                conv = SupportConversation.objects.get(id=ticket_id)
                conv.status = 'closed'
                conv.last_message = system_message
                conv.save()
                
                SupportMessage.objects.create(
                    conversation=conv,
                    sender_id=0,
                    sender_type="system",
                    message=system_message
                )
            except SupportConversation.DoesNotExist:
                pass
            
            # Broadcast closure event
            room_name = f'conversation_{ticket_id}'
            
            now = datetime.datetime.utcnow().isoformat()
            
            # First send the system message text
            async_to_sync(channel_layer.group_send)(
                room_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': msg_id,
                        'conversation_id': ticket_id,
                        'sender_id': 'system',
                        'sender_type': 'system',
                        'message': system_message,
                        'is_system': True,
                        'created_at': now
                    }
                }
            )
            
            # Then send chat_closed event
            async_to_sync(channel_layer.group_send)(
                room_name,
                {
                    'type': 'chat_closed',
                    'conversation_id': ticket_id,
                    'reason': 'timeout'
                }
            )
            logger.info(f"Automatically closed idle ticket {ticket_id}")

    except Exception as e:
        logger.error(f"Error in idle timeout task: {e}")

def start_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        # Run every 10 seconds
        _scheduler.add_job(check_idle_conversations, 'interval', seconds=10)
        _scheduler.start()
        logger.info("Started idle timeout background scheduler.")
