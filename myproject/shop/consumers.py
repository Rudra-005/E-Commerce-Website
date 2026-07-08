import logging
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import SupportConversation, SupportMessage, UserProfile
from mongodb.support_repository import (
    save_support_ticket, save_support_message, 
    reset_idle_status, close_support_ticket
)

logger = logging.getLogger(__name__)

class SupportChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info(f"WS Connect: User {self.scope['user']}, Channel: {self.channel_name}")
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return
            
        # Get role
        self.role = await self.get_user_role(self.user)
        self.room_group_names = []

        if self.role in ['admin', 'support']:
            await self.channel_layer.group_add('admins', self.channel_name)
            self.room_group_names.append('admins')
            
        await self.accept()

    async def disconnect(self, close_code):
        logger.info(f"WS Disconnect: User {self.user}, Code: {close_code}, Channel: {self.channel_name}")
        for room in getattr(self, 'room_group_names', []):
            logger.info(f"WS Discarding Room: {room} for Channel: {self.channel_name}")
            await self.channel_layer.group_discard(room, self.channel_name)

    async def receive(self, text_data):
        logger.info(f"WS Receive from User {self.user}: {text_data}")
        data = json.loads(text_data)
        event_type = data.get('type')
        payload = data.get('payload', {})

        if event_type == 'join_conversation':
            await self.join_conversation(payload.get('conversation_id'))
            
        elif event_type == 'send_message':
            await self.handle_send_message(payload)
            
        elif event_type == 'typing':
            await self.handle_typing(payload, is_typing=True)
            
        elif event_type == 'stop_typing':
            await self.handle_typing(payload, is_typing=False)
            
        elif event_type == 'mark_read':
            await self.handle_mark_read(payload)

        elif event_type == 'continue_chat':
            await self.handle_continue_chat(payload)

        elif event_type == 'end_chat':
            await self.handle_end_chat(payload)

    async def join_conversation(self, conversation_id):
        if not conversation_id:
            return
            
        # Check authorization
        authorized = await self.is_authorized_for_conversation(conversation_id)
        if not authorized:
            return
            
        room_name = f'conversation_{conversation_id}'
        if room_name not in self.room_group_names:
            logger.info(f"WS Adding Room: {room_name} for Channel: {self.channel_name}")
            await self.channel_layer.group_add(room_name, self.channel_name)
            self.room_group_names.append(room_name)

    async def handle_send_message(self, payload):
        conversation_id = payload.get('conversation_id')
        text = payload.get('message')
        message_type = payload.get('message_type', 'text')
        
        if not conversation_id or not text:
            return
            
        authorized = await self.is_authorized_for_conversation(conversation_id)
        if not authorized:
            return
            
        conv = await database_sync_to_async(SupportConversation.objects.get)(id=conversation_id)
        payload_sender = payload.get('sender_type')
        
        if payload_sender == 'admin' and self.role in ['admin', 'support']:
            sender_type = 'admin'
        else:
            sender_type = 'customer'
        
        msg = await self.save_message(conversation_id, text, sender_type, message_type=message_type)
        
        if "[AI SUMMARY]" in text:
            try:
                from chatbot.tasks import process_human_handoff_task
                process_human_handoff_task.delay(conversation_id)
            except Exception as e:
                logger.error(f"Failed to dispatch human handoff task: {e}")
                
        room_name = f'conversation_{conversation_id}'
        event = {
            'type': 'chat_message',
            'message': {
                'id': msg.id,
                'conversation_id': conversation_id,
                'sender_id': self.user.id,
                'sender_type': sender_type,
                'message': text,
                'message_type': message_type,
                'created_at': msg.created_at.isoformat()
            }
        }
        
        logger.info(f"WS Broadcasting chat_message to {room_name}")
        await self.channel_layer.group_send(room_name, event)
        
        # Reset idle status in MongoDB
        await database_sync_to_async(reset_idle_status)(conversation_id)
        
        if sender_type == 'customer':
            await self.channel_layer.group_send('admins', {
                'type': 'conversation_updated',
                'conversation_id': conversation_id,
                'last_message': text,
                'customer_id': self.user.id
            })

    async def handle_typing(self, payload, is_typing):
        conversation_id = payload.get('conversation_id')
        if not conversation_id: return
        room_name = f'conversation_{conversation_id}'
        await self.channel_layer.group_send(room_name, {
            'type': 'typing_indicator',
            'conversation_id': conversation_id,
            'is_typing': is_typing,
            'user_id': self.user.id
        })

    async def handle_mark_read(self, payload):
        conversation_id = payload.get('conversation_id')
        if not conversation_id: return
        
        await self.mark_messages_read(conversation_id)
        room_name = f'conversation_{conversation_id}'
        await self.channel_layer.group_send(room_name, {
            'type': 'messages_read',
            'conversation_id': conversation_id,
            'read_by': self.user.id
        })

    async def handle_continue_chat(self, payload):
        conversation_id = payload.get('conversation_id')
        if not conversation_id: return
        
        authorized = await self.is_authorized_for_conversation(conversation_id)
        if not authorized: return

        # Reset idle status in MongoDB
        await database_sync_to_async(reset_idle_status)(conversation_id)

        # Notify room
        room_name = f'conversation_{conversation_id}'
        await self.channel_layer.group_send(room_name, {
            'type': 'chat_continued',
            'conversation_id': conversation_id,
            'user_id': self.user.id
        })

    async def handle_end_chat(self, payload):
        conversation_id = payload.get('conversation_id')
        if not conversation_id: return
        
        authorized = await self.is_authorized_for_conversation(conversation_id)
        if not authorized: return

        # Close ticket in MongoDB
        await database_sync_to_async(close_support_ticket)(conversation_id)
        
        sender = "admin" if self.role in ['admin', 'support'] else "customer"
        system_message = f"The {sender} ended the chat."
        
        # Save system message
        msg = await self.save_message(conversation_id, system_message, 'system', is_system=True)
        
        # Notify room
        room_name = f'conversation_{conversation_id}'
        
        # First send the system message
        await self.channel_layer.group_send(room_name, {
            'type': 'chat_message',
            'message': {
                'id': msg.id,
                'conversation_id': conversation_id,
                'sender_id': 'system',
                'sender_type': msg.sender_type,
                'message': msg.message,
                'message_type': msg.message_type,
                'is_system': True,
                'created_at': msg.created_at.isoformat()
            }
        })
        
        # Then send chat_closed event
        await self.channel_layer.group_send(room_name, {
            'type': 'chat_closed',
            'conversation_id': conversation_id,
            'reason': f'{sender}_ended'
        })
        
        # Also notify admins to update list
        await self.channel_layer.group_send('admins', {
            'type': 'conversation_updated',
            'conversation_id': conversation_id,
            'customer_id': self.user.id
        })


    # Event handlers for group_send
    async def chat_message(self, event):
        logger.info(f"WS chat_message handler sending to User {self.user}")
        await self.send(text_data=json.dumps({'type': 'receiveMessage', 'payload': event['message']}))

    async def conversation_updated(self, event):
        await self.send(text_data=json.dumps({'type': 'conversationUpdated', 'payload': event}))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({'type': 'typing' if event['is_typing'] else 'stopTyping', 'payload': event}))

    async def messages_read(self, event):
        await self.send(text_data=json.dumps({'type': 'messagesRead', 'payload': event}))

    async def idle_warning(self, event):
        await self.send(text_data=json.dumps({'type': 'idleWarning', 'payload': event}))

    async def chat_continued(self, event):
        await self.send(text_data=json.dumps({'type': 'chatContinued', 'payload': event}))

    async def chat_closed(self, event):
        await self.send(text_data=json.dumps({'type': 'chatClosed', 'payload': event}))


    # DB methods
    @database_sync_to_async
    def get_user_role(self, user):
        if user.is_staff or user.is_superuser:
            return 'admin'
        try:
            return user.userprofile.role
        except UserProfile.DoesNotExist:
            return 'customer'

    @database_sync_to_async
    def is_authorized_for_conversation(self, conv_id):
        if self.user.is_staff or self.user.is_superuser:
            return True
            
        try:
            conv = SupportConversation.objects.get(id=conv_id)
            if self.role in ['admin', 'support']:
                return True
            return conv.customer_id == self.user.id
        except SupportConversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, conv_id, text, sender_type, is_system=False, message_type='text'):
        # PostgreSQL
        conv = SupportConversation.objects.get(id=conv_id)
        if message_type == 'image':
            conv.last_message = "Sent an image"
        else:
            conv.last_message = text
            
        if not is_system:
            conv.status = 'open' if sender_type == 'customer' else 'pending'
        else:
            conv.status = 'closed'
        conv.save()
        
        msg = SupportMessage.objects.create(
            conversation=conv,
            sender_id=self.user.id if not is_system else 0,
            sender_type=sender_type,
            message=text,
            message_type=message_type
        )
        
        # MongoDB
        save_support_ticket(
            ticket_id=conv_id, 
            customer_id=conv.customer_id,
            title=f"Chat #{conv_id}"
        )
        save_support_message(
            ticket_id=conv_id,
            sender_id=self.user.id if not is_system else "system",
            sender_type=sender_type,
            message_content=text,
            is_system=is_system
        )
        
        return msg

    @database_sync_to_async
    def mark_messages_read(self, conv_id):
        # Mark all messages in this conv that are not sent by me as read
        SupportMessage.objects.filter(
            conversation_id=conv_id,
            is_read=False
        ).exclude(sender_id=self.user.id).update(is_read=True)
