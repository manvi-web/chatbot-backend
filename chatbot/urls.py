from django.urls import path
from . import views

urlpatterns = [
    # Chatbot endpoints
    # path("chatbot",         views.chatbot,        name="chatbot"),        # not used by frontend
    path("chatbot/stream",   views.chatbot_stream,   name="chatbot_stream"),
    # path("chatbot/message", views.chat_message,    name="chat_message"),   # not used by frontend
    path("chatbot/options",  views.chatbot_options,  name="chatbot_options"),
    path("chatbot/status",   views.chatbot_status,   name="chatbot_status"),
    path("chatbot/feedback", views.chatbot_feedback, name="chatbot_feedback"),
]
