from django.contrib import admin

from .models import Product, Review


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "price",
        "category",
        "stock"
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):

    list_display = (

        "id",

        "product",

        "customer_name",

        "rating",

        "is_verified_purchase",

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