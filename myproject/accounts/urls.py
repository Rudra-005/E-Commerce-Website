from django.urls import path
from .views import GoogleLoginView, GoogleCallbackView, GoogleAuthView

urlpatterns = [
    path("google/", GoogleAuthView.as_view(), name="google_auth_view"),
    path("google/login/", GoogleLoginView.as_view(), name="google_login"),
    path("google/callback/", GoogleCallbackView.as_view(), name="google_callback"),
]