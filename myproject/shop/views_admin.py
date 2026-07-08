from django.shortcuts import render, redirect
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import Order, Product, RefundRequest
from .decorators import require_role, require_permission

class AdminBaseRedirectView(View):
    """Redirects /admin/ to the appropriate dashboard based on role."""
    def get(self, request):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return redirect("login")
            
        role = getattr(request.user.userprofile, 'role', 'customer')
        if role == 'admin' or request.user.is_superuser:
            return redirect("admin_dashboard")
        elif role == 'support':
            return redirect("admin_chat")
        else:
            return redirect("home")

@method_decorator(require_role(['admin']), name='dispatch')
class AdminDashboardView(View):
    def get(self, request):
        context = {
            'total_users': User.objects.count(),
            'total_orders': Order.objects.count(),
            'total_products': Product.objects.count(),
            'pending_refunds': RefundRequest.objects.filter(status='PENDING').count(),
        }
        return render(request, "admin/dashboard.html", context)

@method_decorator(require_role(['admin', 'support']), name='dispatch')
@method_decorator(require_permission('chat'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AdminChatView(View):
    def get(self, request):
        return render(request, "admin/chat.html")

@method_decorator(require_role(['admin']), name='dispatch')
@method_decorator(require_permission('orders'), name='dispatch')
class AdminOrdersView(View):
    def get(self, request):
        orders = Order.objects.all().order_by('-created_at')[:50]
        return render(request, "admin/orders.html", {'orders': orders})

@method_decorator(require_role(['admin']), name='dispatch')
@method_decorator(require_permission('products'), name='dispatch')
class AdminProductsView(View):
    def get(self, request):
        products = Product.objects.all().order_by('-id')[:50]
        return render(request, "admin/products.html", {'products': products})

@method_decorator(require_role(['admin']), name='dispatch')
@method_decorator(require_permission('users'), name='dispatch')
class AdminUsersView(View):
    def get(self, request):
        users = User.objects.all().order_by('-date_joined')[:50]
        return render(request, "admin/users.html", {'users': users})

@method_decorator(require_role(['admin']), name='dispatch')
@method_decorator(require_permission('analytics'), name='dispatch')
class AdminAnalyticsView(View):
    def get(self, request):
        from django.db.models import Sum
        total_revenue = Order.objects.filter(status__in=['Delivered', 'Shipped', 'Pending']).aggregate(total=Sum('total_price'))['total'] or 0
        total_orders = Order.objects.count()
        total_users = User.objects.count()
        total_products = Product.objects.count()
        
        context = {
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'total_users': total_users,
            'total_products': total_products
        }
        return render(request, "admin/analytics.html", context)

@method_decorator(require_role(['admin']), name='dispatch')
@method_decorator(require_permission('refunds'), name='dispatch')
class AdminRefundsView(View):
    def get(self, request):
        refunds = RefundRequest.objects.all().order_by('-created_at')[:50]
        return render(request, "admin/refunds.html", {'refunds': refunds})

import razorpay
from django.conf import settings
import json
from django.http import JsonResponse
from .models import RefundTransaction

@method_decorator(require_role(['admin']), name='dispatch')
@method_decorator(require_permission('refunds'), name='dispatch')
class AdminProcessRefundAPIView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            refund_id = data.get('refund_id')
            action = data.get('action') # 'approve' or 'reject'
            
            refund_req = RefundRequest.objects.get(id=refund_id)
            if refund_req.status != 'Pending':
                return JsonResponse({'success': False, 'error': f'Refund is already {refund_req.status}'})
                
            if action == 'reject':
                refund_req.status = 'Rejected'
                refund_req.save()
                return JsonResponse({'success': True, 'message': 'Refund rejected successfully'})
                
            elif action == 'approve':
                order = refund_req.order
                if not order.razorpay_payment_id:
                    return JsonResponse({'success': False, 'error': 'Order has no Razorpay Payment ID.'})
                    
                client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                
                try:
                    refund_data = client.payment.refund(order.razorpay_payment_id, {})
                    RefundTransaction.objects.create(
                        refund_request=refund_req,
                        amount=order.total_price,
                        transaction_id=refund_data.get('id'),
                        status='Success'
                    )
                    refund_req.status = 'Approved'
                    refund_req.save()
                    order.status = 'Refunded'
                    order.save()
                    
                    return JsonResponse({'success': True, 'message': 'Refund approved and processed via Razorpay'})
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    RefundTransaction.objects.create(
                        refund_request=refund_req,
                        amount=order.total_price,
                        status='Failed'
                    )
                    if "invalid request" in error_msg or "badrequest" in error_msg:
                        return JsonResponse({'success': False, 'error': 'Razorpay rejected it. This usually means you need to add test funds to your Razorpay balance.'})
                    else:
                        return JsonResponse({'success': False, 'error': f'Razorpay error: {str(e)}'})
            else:
                return JsonResponse({'success': False, 'error': 'Invalid action'})
                
        except RefundRequest.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Refund not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

@method_decorator(require_role(['admin']), name='dispatch')
@method_decorator(require_permission('settings'), name='dispatch')
class AdminSettingsView(View):
    def get(self, request):
        return render(request, "admin/settings.html")

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_role(['admin']), name='dispatch')
class AdminEmailCampaignsView(View):
    def get(self, request):
        from shop.models import AIEmailCampaign, AIEmailLog
        campaigns = AIEmailCampaign.objects.all().order_by('-created_at')
        logs = AIEmailLog.objects.all().order_by('-sent_at')[:50]
        active_campaign = AIEmailCampaign.objects.filter(is_active=True).first()

        context = {
            'campaigns': campaigns,
            'logs': logs,
            'active_campaign': active_campaign,
        }
        return render(request, "admin/email_campaigns.html", context)

    def _sync_celery_beat(self, campaign):
        """Dynamically updates the Celery Beat task interval for the campaign."""
        from django_celery_beat.models import IntervalSchedule, PeriodicTask
        
        # If campaign is not active or deleted, disable the task
        if not campaign or not campaign.is_active:
            PeriodicTask.objects.filter(name='Send AI Email Campaign (Every 1 Minute)').update(enabled=False)
            PeriodicTask.objects.filter(name='Send AI Email Campaign').update(enabled=False)
            return

        # Translate schedule unit to Celery Beat period
        period_map = {
            'Minutes': IntervalSchedule.MINUTES,
            'Hours': IntervalSchedule.HOURS,
            'Days': IntervalSchedule.DAYS,
            'Weeks': IntervalSchedule.DAYS, # Weeks mapped to days * 7
        }

        period = period_map.get(campaign.schedule_unit, IntervalSchedule.MINUTES)
        every = campaign.schedule_value
        if campaign.schedule_unit == 'Weeks':
            every = campaign.schedule_value * 7

        # Find or create IntervalSchedule
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=every,
            period=period
        )

        # Deactivate any legacy 1-min hardcoded beat task to prevent duplicates
        PeriodicTask.objects.filter(name='Send AI Email Campaign (Every 1 Minute)').update(enabled=False)

        # Create or update main Send AI Email Campaign task
        periodic_task, created = PeriodicTask.objects.update_or_create(
            name='Send AI Email Campaign',
            defaults={
                'task': 'shop.tasks.send_ai_email_campaign_task',
                'interval': schedule,
                'enabled': True,
                'queue': 'email',
                'description': f"Triggers AI email campaign '{campaign.topic}' dynamically",
            }
        )

    def post(self, request):
        from shop.models import AIEmailCampaign, AIEmailLog
        from django.contrib import messages
        
        action = request.POST.get('action')
        
        if action == 'save_campaign':
            topic = request.POST.get('topic', '').strip()
            languages = request.POST.get('languages', 'English, Hindi, Spanish, French').strip()
            is_active = request.POST.get('is_active') == 'true'
            
            # Extract schedule values
            try:
                schedule_value = int(request.POST.get('schedule_value', 1))
                if schedule_value < 1:
                    schedule_value = 1
            except ValueError:
                schedule_value = 1
                
            schedule_unit = request.POST.get('schedule_unit', 'Minutes')
            if schedule_unit not in ['Minutes', 'Hours', 'Days', 'Weeks']:
                schedule_unit = 'Minutes'

            campaign_id = request.POST.get('campaign_id')
            
            if not topic:
                messages.error(request, "Please enter a campaign topic.")
                return redirect('admin_email_campaigns')
                
            if is_active:
                # Deactivate other campaigns
                AIEmailCampaign.objects.all().update(is_active=False)
                
            if campaign_id:
                campaign = AIEmailCampaign.objects.get(id=campaign_id)
                campaign.topic = topic
                campaign.languages = languages
                campaign.schedule_value = schedule_value
                campaign.schedule_unit = schedule_unit
                campaign.is_active = is_active
                campaign.save()
                messages.success(request, f"Campaign '{topic}' updated successfully.")
            else:
                campaign = AIEmailCampaign.objects.create(
                    topic=topic,
                    languages=languages,
                    schedule_value=schedule_value,
                    schedule_unit=schedule_unit,
                    is_active=is_active
                )
                messages.success(request, f"New campaign '{topic}' created successfully.")

            # Sync with Celery Beat Scheduler
            self._sync_celery_beat(campaign)
                
        elif action == 'toggle_active':
            campaign_id = request.POST.get('campaign_id')
            campaign = AIEmailCampaign.objects.get(id=campaign_id)
            if not campaign.is_active:
                # Deactivate other campaigns
                AIEmailCampaign.objects.all().update(is_active=False)
                campaign.is_active = True
                messages.success(request, f"Campaign '{campaign.topic}' is now active.")
                self._sync_celery_beat(campaign)
            else:
                campaign.is_active = False
                messages.success(request, f"Campaign '{campaign.topic}' is now deactivated.")
                self._sync_celery_beat(campaign)
            campaign.save()
            
        elif action == 'delete_campaign':
            campaign_id = request.POST.get('campaign_id')
            campaign = AIEmailCampaign.objects.get(id=campaign_id)
            topic = campaign.topic
            
            # If deleting the currently active campaign, make sure to disable Celery Beat task
            if campaign.is_active:
                campaign.is_active = False
                self._sync_celery_beat(campaign)
                
            campaign.delete()
            messages.success(request, f"Campaign '{topic}' deleted successfully.")
            
        elif action == 'trigger_now':
            # Manually trigger the email campaign task asynchronously
            from shop.tasks import send_ai_email_campaign_task
            send_ai_email_campaign_task.delay()
            messages.success(request, "AI Email Campaign task triggered successfully in Celery.")
            
        return redirect('admin_email_campaigns')

