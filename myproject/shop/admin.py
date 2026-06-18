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
