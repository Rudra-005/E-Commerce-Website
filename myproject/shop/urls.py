from django.urls import path

from .views import (
    home,
    product_detail,
    search_suggestions,
    add_to_cart,
    cart_view,
    remove_from_cart,
    increase_quantity,
    decrease_quantity,
    clear_cart,
    checkout_view
)

urlpatterns = [

    path(
        "",
        home,
        name="home"
    ),

    path(
        "product/<int:product_id>/",
        product_detail,
        name="product_detail"
    ),

    path(
        "search-suggestions/",
        search_suggestions,
        name="search_suggestions"
    ),

    path(
        "add-to-cart/<int:product_id>/",
        add_to_cart,
        name="add_to_cart"
    ),

    path(
        "cart/",
        cart_view,
        name="cart"
    ),

    path(
        "remove-from-cart/<int:product_id>/",
        remove_from_cart,
        name="remove_from_cart"
    ),

    path(
        "increase-quantity/<int:product_id>/",
        increase_quantity,
        name="increase_quantity"
    ),

    path(
        "decrease-quantity/<int:product_id>/",
        decrease_quantity,
        name="decrease_quantity"
    ),

    path(
        "clear-cart/",
        clear_cart,
        name="clear_cart"
    ),

    path(
        "checkout/",
        checkout_view,
        name="checkout"
    ),
]