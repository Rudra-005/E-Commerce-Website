from django.contrib.auth.models import AnonymousUser, User

from .auth_helpers import (
    verify_token,
    generate_access_token
)


class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/django-admin/'):
            if request.user.is_authenticated and not request.user.is_staff:
                from django.contrib.auth import logout
                logout(request)
            return self.get_response(request)

        access_token = request.COOKIES.get("access_token")
        refresh_token = request.COOKIES.get("refresh_token")

        # Keep track of the session-authenticated user (e.g. from django-allauth)
        session_user = request.user if getattr(request.user, "is_authenticated", False) else None

        request.user = AnonymousUser()

        new_access_token = None

        # ==========================
        # ACCESS TOKEN CHECK
        # ==========================

        if access_token:

            payload = verify_token(
                access_token,
                "access"
            )

            if payload:
                try:
                    request.user = User.objects.get(
                        id=payload["user_id"]
                    )
                except User.DoesNotExist:
                    request.user = AnonymousUser()

        # ==========================
        # REFRESH TOKEN CHECK
        # ==========================

        if not getattr(request.user, "is_authenticated", False) and refresh_token:

            payload = verify_token(
                refresh_token,
                "refresh"
            )

            if payload:

                try:
                    request.user = User.objects.get(
                        id=payload["user_id"]
                    )

                    class TempUser:
                        pass

                    temp_user = TempUser()
                    temp_user.id = request.user.id
                    temp_user.username = request.user.username
                    temp_user.email = request.user.email

                    new_access_token = generate_access_token(
                        temp_user
                    )

                except User.DoesNotExist:
                    request.user = AnonymousUser()

        # ==========================
        # SESSION FALLBACK CHECK
        # ==========================
        if not getattr(request.user, "is_authenticated", False) and session_user:
            request.user = session_user

        response = self.get_response(request)

        # ==========================
        # ISSUE NEW ACCESS TOKEN
        # ==========================

        if new_access_token:

            response.set_cookie(
                key="access_token",
                value=new_access_token,
                httponly=True,
                samesite="Lax",
                secure=False
            )

        return response
import time

def force_sync_session_cart(request):
    """Force synchronize all items in the session cart to the database immediately."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return
        
    cart = request.session.get('session_cart', {})
    if not cart:
        return
        
    from shop.models import Cart
    to_remove = []
    
    for pid, data in cart.items():
        c, created = Cart.objects.get_or_create(user=request.user, product_id=pid)
        if not created:
            c.quantity += data.get('quantity', 1)
        else:
            c.quantity = data.get('quantity', 1)
        c.save()
        to_remove.append(pid)
        
    for pid in to_remove:
        del cart[pid]
        
    request.session['session_cart'] = cart
    request.session.modified = True

class CartSessionSyncMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(request, 'user', None) and request.user.is_authenticated:
            cart = request.session.get('session_cart', {})
            now = time.time()
            to_remove = []
            modified = False
            
            for pid, data in cart.items():
                if now - data.get('added_at', now) > 300: # 5 minutes
                    from shop.models import Cart
                    c, created = Cart.objects.get_or_create(user=request.user, product_id=pid)
                    if not created:
                        c.quantity += data.get('quantity', 1)
                    else:
                        c.quantity = data.get('quantity', 1)
                    c.save()
                    to_remove.append(pid)
                    modified = True
            
            for pid in to_remove:
                del cart[pid]
                
            if modified:
                request.session['session_cart'] = cart
                request.session.modified = True
                
        return self.get_response(request)
