from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('chat/', views.ChatAPIView.as_view(), name='chat'),
    path('chat/history/', views.ChatHistoryAPIView.as_view(), name='chat_history'),
    path('chat/history/delete/', views.ChatHistoryDeleteAPIView.as_view(), name='chat_history_delete'),
]
