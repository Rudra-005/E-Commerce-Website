from django.contrib import admin
from django.db.models import Avg, Count
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Product, Review, Category, Cart, UserProfile, Address

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class AddressInline(admin.StackedInline):
    model = Address
    extra = 1

# Unregister the default User Admin
admin.site.unregister(User)

# Register the new User Admin with Inlines
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    inlines = (AddressInline,)

admin.site.register(Address)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "slug",
        "product_count"
    )

    search_fields = ("name",)

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Products"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "price",
        "category",
        "category_fk",
        "stock",
        "avg_rating",
        "review_count"
    )

    list_filter = (
        "category",
        "category_fk",
    )

    search_fields = ("name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            _avg_rating=Avg("reviews__rating"),
            _review_count=Count("reviews")
        )
        return qs

    def avg_rating(self, obj):
        val = obj._avg_rating
        return round(val, 1) if val else "0"

    avg_rating.short_description = "Avg Rating"
    avg_rating.admin_order_field = "_avg_rating"

    def review_count(self, obj):
        return obj._review_count

    review_count.short_description = "Reviews"
    review_count.admin_order_field = "_review_count"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "product",
        "customer_name",
        "rating",
        "title",
        "is_verified_purchase",
        "helpful_count",
        "created_at"
    )

    list_filter = (
        "rating",
        "is_verified_purchase"
    )

    search_fields = (
        "customer_name",
        "product__name"
    )


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "product",
        "quantity",
        "subtotal"
    )

    def subtotal(self, obj):
        return obj.subtotal

    subtotal.short_description = "Subtotal"


from .models import ShippingAddress, Order, OrderItem

admin.site.register(ShippingAddress)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total_price", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "id")
    inlines = (OrderItemInline,)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "price", "item_subtotal")
    list_filter = ("order__status",)
    search_fields = ("product__name", "order__id", "order__user__username")
    raw_id_fields = ("order", "product")

    def item_subtotal(self, obj):
        return obj.price * obj.quantity
    item_subtotal.short_description = "Subtotal"


from .models import StockNotification

@admin.register(StockNotification)
class StockNotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "product", "created_at", "notified")
    list_filter = ("notified", "created_at")
    search_fields = ("email", "product__name")


from .models import RefundRequest, RefundTransaction

class RefundTransactionInline(admin.StackedInline):
    model = RefundTransaction
    can_delete = False

import razorpay
from django.conf import settings
from django.contrib import messages
from django.utils.translation import ngettext

@admin.action(description="Accept & Process Selected Refunds (Razorpay)")
def process_refunds(modeladmin, request, queryset):
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    except AttributeError:
        messages.error(request, "Razorpay credentials not found in settings.")
        return

    success_count = 0
    
    for refund_req in queryset:
        if refund_req.status != 'Pending':
            continue
            
        order = refund_req.order
        if not order.razorpay_payment_id:
            messages.error(request, f"Order #{order.id} has no Razorpay Payment ID.")
            continue
            
        try:
            # We pass an empty dict to process a full refund automatically 
            # without risking floating point mismatch.
            refund_data = client.payment.refund(
                order.razorpay_payment_id,
                {}
            )
            
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
            
            success_count += 1
            
        except Exception as e:
            error_msg = str(e).lower()
            if "invalid request" in error_msg or "badrequest" in error_msg:
                messages.error(request, f"Failed to refund Order #{order.id}: Razorpay rejected it. This usually means you need to click 'Add Funds' in your Razorpay Test Dashboard because your test balance is low.")
            else:
                messages.error(request, f"Failed to refund Order #{order.id}: {str(e)}")
            
            RefundTransaction.objects.create(
                refund_request=refund_req,
                amount=order.total_price,
                status='Failed'
            )
            
    if success_count > 0:
        messages.success(request, f"Successfully processed {success_count} refund(s) via Razorpay.")

@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "order__id")
    inlines = (RefundTransactionInline,)
    actions = [process_refunds]

@admin.register(RefundTransaction)
class RefundTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "refund_request", "amount", "status", "processed_at")
    list_filter = ("status", "processed_at")
    search_fields = ("refund_request__order__id", "transaction_id")

from .models import SubscriptionPlan, UserSubscription

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'billing_cycle', 'is_active', 'razorpay_plan_id')
    list_filter = ('billing_cycle', 'is_active')
    search_fields = ('name', 'razorpay_plan_id')

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscription_plan', 'status', 'start_date', 'end_date', 'auto_renew')
    list_filter = ('status', 'auto_renew')
    search_fields = ('user__username', 'razorpay_subscription_id')

