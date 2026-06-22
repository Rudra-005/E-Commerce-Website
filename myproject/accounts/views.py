from django.shortcuts import render, redirect
import json
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from .models import SocialAccount
from shop.auth_helpers import generate_tokens


class GoogleLoginView(View):
    """View to initiate Google OAuth login redirect."""
    def get(self, request):
        google_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            "?response_type=code"
            f"&client_id={settings.GOOGLE_CLIENT_ID}"
            f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
            "&scope=openid%20email%20profile"
        )
        return redirect(google_url)


@method_decorator(csrf_exempt, name="dispatch")
class GoogleCallbackView(View):
    """View to handle OAuth callback from Google."""
    def post(self, request):
        # Delegate post credentials verification to GoogleAuthView
        return GoogleAuthView().post(request)

    def get(self, request):
        code = request.GET.get('code')
        if not code:
            return JsonResponse({'error': 'Missing authorization code'}, status=400)

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'code': code,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }

        try:
            token_res = requests.post(token_url, data=data)
            token_data = token_res.json()

            if 'error' in token_data:
                return JsonResponse({'error': token_data.get('error_description', 'Failed to exchange code for token')}, status=400)

            google_token = token_data.get('id_token')
            if not google_token:
                return JsonResponse({'error': 'Missing ID token from Google response'}, status=400)

            client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '638655157320-kb62hj2vckv9e0sfdk1vjbmfbhmsue35.apps.googleusercontent.com')
            
            id_info = id_token.verify_oauth2_token(
                google_token, 
                google_requests.Request(), 
                client_id
            )

            google_uid = id_info.get('sub')
            email = id_info.get('email')
            first_name = id_info.get('given_name', '')
            last_name = id_info.get('family_name', '')

            if not google_uid or not email:
                return JsonResponse({'error': 'Malformed identification data returned from provider'}, status=400)

            if not id_info.get('email_verified'):
                return JsonResponse({'error': 'Google account email remains unverified.'}, status=400)

            try:
                # Query if this Google Social Account already has a mapped record
                social_account = SocialAccount.objects.get(provider='google', unique_id=google_uid)
                user = social_account.user
                created = False
            except SocialAccount.DoesNotExist:
                # Look up if an existing user was registered with this specific email address
                user = User.objects.filter(email__iexact=email).first()
                if not user:
                    base_username = email.split('@')[0]
                    username = base_username
                    counter = 1
                    while User.objects.filter(username__iexact=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1
                    
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name
                    )
                
                # Map the user record to this new Social Provider account
                social_account = SocialAccount.objects.create(
                    user=user,
                    provider='google',
                    unique_id=google_uid,
                    extra_data=id_info
                )
                created = True

            access_token, refresh_token = generate_tokens(user)
            
            response = redirect("home")
            
            response.set_cookie(
                "access_token",
                access_token,
                httponly=True,
                samesite="Lax",
                secure=not settings.DEBUG
            )
            response.set_cookie(
                "refresh_token",
                refresh_token,
                httponly=True,
                samesite="Lax",
                secure=not settings.DEBUG
            )
            
            return response

        except ValueError as e:
            return JsonResponse({'error': f'Invalid signatures on external Google Auth Token: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class GoogleAuthView(View):
    """View to handle client-side credential/token verification."""
    def post(self, request):
        try:
            is_json = (request.content_type == 'application/json')
            if is_json:
                body = json.loads(request.body)
                google_token = body.get('token')
            else:
                google_token = request.POST.get('credential')

            if not google_token:
                return JsonResponse({'error': 'Missing ID token'}, status=400)

            # 1. Decode and verify validity against Google Auth Infrastructure
            client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '638655157320-kb62hj2vckv9e0sfdk1vjbmfbhmsue35.apps.googleusercontent.com')
            
            try:
                id_info = id_token.verify_oauth2_token(
                    google_token, 
                    google_requests.Request(), 
                    client_id,
                    clock_skew_in_seconds=300
                )
            except ValueError as verify_err:
                if settings.DEBUG:
                    import jwt as pyjwt
                    # Fallback decode without signature check in debug/dev mode
                    id_info = pyjwt.decode(
                        google_token,
                        options={"verify_signature": False},
                        algorithms=["RS256"]
                    )
                    # Verify audience and issuer to maintain basic checks
                    if id_info.get('aud') != client_id:
                        return JsonResponse({'error': 'Token audience mismatch'}, status=400)
                    if id_info.get('iss') not in ('accounts.google.com', 'https://accounts.google.com'):
                        return JsonResponse({'error': 'Token issuer mismatch'}, status=400)
                else:
                    raise verify_err

            # 2. Extract context parameters
            google_uid = id_info.get('sub')  # Persistent tracking key unique to the Google profile
            email = id_info.get('email')
            first_name = id_info.get('given_name', '')
            last_name = id_info.get('family_name', '')

            if not google_uid or not email:
                return JsonResponse({'error': 'Malformed identification data returned from provider'}, status=400)

            # CRITICAL SECURITY CHECK: Enforce that Google confirms ownership of the email channel
            if not id_info.get('email_verified'):
                return JsonResponse({'error': 'Google account email remains unverified.'}, status=400)

            # 3. Stepwise mapping check to avoid split-profile duplication
            try:
                # Query if this Google Social Account already has a mapped record
                social_account = SocialAccount.objects.get(provider='google', unique_id=google_uid)
                user = social_account.user
                created = False
            except SocialAccount.DoesNotExist:
                # Look up if an existing user was registered with this specific email address
                user = User.objects.filter(email__iexact=email).first()
                if not user:
                    # First time user is visiting: provision base user structural identity
                    base_username = email.split('@')[0]
                    username = base_username
                    counter = 1
                    while User.objects.filter(username__iexact=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1
                    
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name
                    )
                
                # Map the user record to this new Social Provider account
                social_account = SocialAccount.objects.create(
                    user=user,
                    provider='google',
                    unique_id=google_uid,
                    extra_data=id_info
                )
                created = True

            # 4. Sign token matching existing application architecture specs
            access_token, refresh_token = generate_tokens(user)
            
            if is_json:
                response = JsonResponse({
                    'access_token': access_token,
                    'is_new_user': created
                })
            else:
                response = redirect("home")
            
            # Set signed pyjwt tokens nested within HttpOnly Secure Lax cookies
            response.set_cookie(
                "access_token",
                access_token,
                httponly=True,
                samesite="Lax",
                secure=not settings.DEBUG
            )
            response.set_cookie(
                "refresh_token",
                refresh_token,
                httponly=True,
                samesite="Lax",
                secure=not settings.DEBUG
            )
            
            return response

        except ValueError as e:
            return JsonResponse({'error': f'Invalid signatures on external Google Auth Token: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class RegisterView(APIView):
    """DRF API view for user registration."""
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')

        if User.objects.filter(username=username).exists():
            return Response({
                "error": "Username already exists"
            })

        if User.objects.filter(email__iexact=email).exists():
            return Response({
                "error": "An account with this email already exists"
            })

        User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        return Response({
            "message": "User registered successfully"
        })
