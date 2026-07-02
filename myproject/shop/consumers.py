import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import SupportConversation, SupportMessage, UserProfile

class SupportChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
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
        for room in self.room_group_names:
            await self.channel_layer.group_discard(room, self.channel_name)

    async def receive(self, text_data):
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

    async def join_conversation(self, conversation_id):
        if not conversation_id:
            return
            
        # Check authorization
        authorized = await self.is_authorized_for_conversation(conversation_id)
        if not authorized:
            return
            
        room_name = f'conversation_{conversation_id}'
        if room_name not in self.room_group_names:
            await self.channel_layer.group_add(room_name, self.channel_name)
            self.room_group_names.append(room_name)

    async def handle_send_message(self, payload):
        conversation_id = payload.get('conversation_id')
        text = payload.get('message')
        
        if not conversation_id or not text:
            return
            
        authorized = await self.is_authorized_for_conversation(conversation_id)
        if not authorized:
            return
            
        conv = await database_sync_to_async(SupportConversation.objects.get)(id=conversation_id)
        if self.user.id == conv.customer_id:
            sender_type = 'customer'
        else:
            sender_type = 'admin' if self.role in ['admin', 'support'] else 'customer'
        
        msg = await self.save_message(conversation_id, text, sender_type)
        
        room_name = f'conversation_{conversation_id}'
        event = {
            'type': 'chat_message',
            'message': {
                'id': msg.id,
                'conversation_id': conversation_id,
                'sender_id': self.user.id,
                'sender_type': sender_type,
                'message': text,
                'created_at': msg.created_at.isoformat()
            }
        }
        
        await self.channel_layer.group_send(room_name, event)
        
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

    # Event handlers for group_send
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'type': 'receiveMessage', 'payload': event['message']}))

    async def conversation_updated(self, event):
        await self.send(text_data=json.dumps({'type': 'conversationUpdated', 'payload': event}))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({'type': 'typing' if event['is_typing'] else 'stopTyping', 'payload': event}))

    async def messages_read(self, event):
        await self.send(text_data=json.dumps({'type': 'messagesRead', 'payload': event}))

    # DB methods
    @database_sync_to_async
    def get_user_role(self, user):
        try:
            return user.userprofile.role
        except UserProfile.DoesNotExist:
            return 'customer'

    @database_sync_to_async
    def is_authorized_for_conversation(self, conv_id):
        try:
            conv = SupportConversation.objects.get(id=conv_id)
            if self.role in ['admin', 'support']:
                return True
            return conv.customer_id == self.user.id
        except SupportConversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, conv_id, text, sender_type):
        conv = SupportConversation.objects.get(id=conv_id)
        conv.last_message = text
        conv.status = 'open' if sender_type == 'customer' else 'pending'
        conv.save()
        
        msg = SupportMessage.objects.create(
            conversation=conv,
            sender_id=self.user.id,
            sender_type=sender_type,
            message=text
        )
        return msg

    @database_sync_to_async
    def mark_messages_read(self, conv_id):
        # Mark all messages in this conv that are not sent by me as read
        SupportMessage.objects.filter(
            conversation_id=conv_id,
            is_read=False
        ).exclude(sender_id=self.user.id).update(is_read=True)
