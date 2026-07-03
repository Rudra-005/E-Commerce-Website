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
        return render(request, "admin/analytics.html")

@method_decorator(require_role(['admin']), name='dispatch')
@method_decorator(require_permission('refunds'), name='dispatch')
class AdminRefundsView(View):
    def get(self, request):
        refunds = RefundRequest.objects.all().order_by('-created_at')[:50]
        return render(request, "admin/refunds.html", {'refunds': refunds})

@method_decorator(require_role(['admin']), name='dispatch')
@method_decorator(require_permission('settings'), name='dispatch')
class AdminSettingsView(View):
    def get(self, request):
        return render(request, "admin/settings.html")
