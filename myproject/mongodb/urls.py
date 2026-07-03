from django.urls import path
from . import admin_views

app_name = 'mongodb'

urlpatterns = [
    path('admin/api/chatbot-conversations/', admin_views.AdminChatbotConversationsView.as_view(), name='admin_chatbot_conversations'),
    path('admin/api/support-conversations/', admin_views.AdminSupportConversationsView.as_view(), name='admin_support_conversations'),
]
