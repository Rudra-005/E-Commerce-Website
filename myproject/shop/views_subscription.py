import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from shop.decorators import jwt_login_required
from shop.models import SubscriptionPlan, UserSubscription
from shop.services.subscription_service import (
    create_razorpay_subscription,
    verify_razorpay_signature,
    sync_subscription_status,
    cancel_subscription,
    get_active_subscription
)
from django.conf import settings

logger = logging.getLogger(__name__)

class MembershipView(View):
    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('amount')
        active_sub = get_active_subscription(request.user) if request.user.is_authenticated else None
        
        return render(request, 'shop/membership.html', {
            'plans': plans,
            'active_sub': active_sub,
            'RAZORPAY_KEY_ID': settings.RAZORPAY_KEY_ID
        })

@method_decorator(jwt_login_required, name='dispatch')
class SubscribeAPIView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            plan_id = data.get('plan_id')
            
            if not plan_id:
                return JsonResponse({'error': 'Plan ID is required'}, status=400)
                
            user_sub, rzp_sub = create_razorpay_subscription(request.user, plan_id)
            
            return JsonResponse({
                'subscription_id': rzp_sub['id'],
                'key_id': settings.RAZORPAY_KEY_ID,
                'user_name': request.user.get_full_name() or request.user.username,
                'user_email': request.user.email
            })
        except Exception as e:
            logger.error(f"Subscription creation failed: {e}")
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(jwt_login_required, name='dispatch')
class ManageSubscriptionAPIView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            action = data.get('action')
            sub_id = data.get('subscription_id')
            
            if action == 'cancel':
                success = cancel_subscription(sub_id)
                if success:
                    return JsonResponse({'success': True, 'message': 'Subscription cancelled successfully.'})
                return JsonResponse({'error': 'Failed to cancel subscription.'}, status=400)
                
            return JsonResponse({'error': 'Invalid action'}, status=400)
        except Exception as e:
            logger.error(f"Manage subscription failed: {e}")
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(View):
    def post(self, request):
        try:
            webhook_signature = request.headers.get('X-Razorpay-Signature')
            payload_body = request.body
            
            if not verify_razorpay_signature(payload_body, webhook_signature):
                return JsonResponse({'error': 'Invalid signature'}, status=400)
                
            payload = json.loads(payload_body)
            event = payload.get('event')
            
            if event in ['subscription.activated', 'subscription.charged', 'subscription.cancelled', 'subscription.completed', 'subscription.halted']:
                subscription_entity = payload['payload']['subscription']['entity']
                rzp_sub_id = subscription_entity['id']
                
                sync_subscription_status(rzp_sub_id)
                
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            return JsonResponse({'error': str(e)}, status=500)
