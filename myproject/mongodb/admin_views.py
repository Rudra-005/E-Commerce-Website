from django.http import JsonResponse
from django.views import View
from .mongo import get_db

class AdminChatbotConversationsView(View):
    def get(self, request):
        db = get_db()
        if db is None:
            return JsonResponse({'error': 'MongoDB not available'}, status=500)
            
        user_id = request.GET.get('user_id')
        conv_id = request.GET.get('conversation_id')
        
        query = {"conversation_type": "chatbot"}
        if user_id:
            query["user_id"] = int(user_id) if user_id.isdigit() else user_id
        if conv_id:
            query["conversation_id"] = conv_id
            
        conversations = list(db.conversations.find(query, {"_id": 0}).sort("updated_at", -1))
        return JsonResponse({'conversations': conversations})

class AdminSupportConversationsView(View):
    def get(self, request):
        db = get_db()
        if db is None:
            return JsonResponse({'error': 'MongoDB not available'}, status=500)
            
        customer_id = request.GET.get('customer_id')
        ticket_id = request.GET.get('ticket_id')
        
        query = {"conversation_type": "support"}
        if customer_id:
            query["customer_id"] = int(customer_id) if customer_id.isdigit() else customer_id
        if ticket_id:
            query["ticket_id"] = ticket_id
            
        conversations = list(db.support_conversations.find(query, {"_id": 0}).sort("updated_at", -1))
        return JsonResponse({'conversations': conversations})
