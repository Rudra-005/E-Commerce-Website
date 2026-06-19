from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('chat/', views.chat_api, name='chat'),
    path('chat/history/', views.chat_history_api, name='chat_history'),
    path('chat/history/delete/', views.chat_history_delete_api, name='chat_history_delete'),
]
