from django.urls import path
from .views import google_login, google_callback, google_auth_view

urlpatterns = [
    path("google/", google_auth_view, name="google_auth_view"),
    path("google/login/", google_login, name="google_login"),
    path("google/callback/", google_callback, name="google_callback"),
]