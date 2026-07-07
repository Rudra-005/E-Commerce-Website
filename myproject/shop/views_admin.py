from django.shortcuts import render, redirect
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.contrib.auth.models import User
from .models import Order, Product, RefundRequest
from .decorators import require_role, require_permission

class AdminBaseRedirectView(View):
    """Redirects /admin/ to the appropriate dashboard based on role."""
    def get(self, request):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return redirect("login")
            
        role = getattr(request.user.userprofile, 'role', 'customer')
        if role == 'admin':
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
