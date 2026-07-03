import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import SupportConversation, SupportMessage
from .decorators import require_role

@method_decorator(csrf_exempt, name='dispatch')
class AdminConversationsAPIView(View):
    @method_decorator(require_role(['admin', 'support']))
    def get(self, request):
        conversations = SupportConversation.objects.select_related('customer').all().order_by('-updated_at')[:50]
        data = []
        for c in conversations:
            unread_count = c.messages.filter(is_read=False).exclude(sender_id=request.user.id).count()
            data.append({
                'id': c.id,
                'customer_name': c.customer.username,
                'customer_email': c.customer.email,
                'status': c.status,
                'priority': c.priority,
                'last_message': c.last_message,
                'last_message_at': c.last_message_at.isoformat() if c.last_message_at else None,
                'unread_count': unread_count,
            })
        return JsonResponse({'conversations': data})

@method_decorator(csrf_exempt, name='dispatch')
class ConversationMessagesAPIView(View):
    def get(self, request, conversation_id):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
            
        try:
            conv = SupportConversation.objects.get(id=conversation_id)
        except SupportConversation.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)
            
        # Auth check
        role = getattr(request.user.userprofile, 'role', 'customer') if hasattr(request.user, 'userprofile') else 'customer'
        if role not in ['admin', 'support'] and conv.customer_id != request.user.id:
            return JsonResponse({'error': 'Forbidden'}, status=403)
            
        messages = conv.messages.all().order_by('created_at')
        data = []
        for m in messages:
            data.append({
                'id': m.id,
                'sender_id': m.sender_id,
                'sender_type': m.sender_type,
                'message': m.message,
                'created_at': m.created_at.isoformat()
            })
            
        return JsonResponse({'messages': data})

@method_decorator(csrf_exempt, name='dispatch')
class CustomerConversationAPIView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
            
        # Get or create conversation for customer
        conv, created = SupportConversation.objects.get_or_create(
            customer=request.user,
            defaults={'status': 'open', 'priority': 'low'}
        )
        
        return JsonResponse({
            'conversation_id': conv.id,
            'status': conv.status
        })

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid

@method_decorator(csrf_exempt, name='dispatch')
class UploadChatImageAPIView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
            
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No image provided'}, status=400)
            
        image_file = request.FILES['image']
        
        # Validate extension
        ext = image_file.name.split('.')[-1].lower()
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            return JsonResponse({'error': 'Invalid file type'}, status=400)
            
        # Generate unique name
        filename = f"chat_images/{uuid.uuid4().hex}.{ext}"
        
        # Save file
        path = default_storage.save(filename, ContentFile(image_file.read()))
        
        # Get public URL
        url = default_storage.url(path)
        
        return JsonResponse({'url': url})
