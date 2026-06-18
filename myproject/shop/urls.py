from django.urls import path
from . import views

urlpatterns = [

    # Home
    path(
        "",
        views.home,
        name="home"
    ),

    # Product Detail
    path(
        "product/<int:product_id>/",
        views.product_detail,
        name="product_detail"
    ),


    # Search
    path(
        "search-suggestions/",
        views.search_suggestions,
        name="search_suggestions"
    ),

    # Dedicated Products List Page
    path(
        "products/",
        views.products_list,
        name="products_list"
    ),

    # Cart
    path(
        "cart/",
        views.cart,
        name="cart"
    ),

    path(
        "add-to-cart/<int:product_id>/",
        views.add_to_cart,
        name="add_to_cart"
    ),

    path(
        "remove-from-cart/<int:product_id>/",
        views.remove_from_cart,
        name="remove_from_cart"
    ),

    path(
        "increase-quantity/<int:product_id>/",
        views.increase_quantity,
        name="increase_quantity"
    ),

    path(
        "decrease-quantity/<int:product_id>/",
        views.decrease_quantity,
        name="decrease_quantity"
    ),

    path(
        "clear-cart/",
        views.clear_cart,
        name="clear_cart"
    ),

    # Checkout
    path(
        "checkout/",
        views.checkout_view,
        name="checkout"
    ),

    # Login
    path(
    "login/",
    views.login_view,
    name="login"
    ),

    # Signup
    path(
        "signup/",
        views.signup_page,
        name="signup"
    ),
    path(
    "logout/",
    views.logout_view,
    name="logout"
    ),

    # OTP
    path(
        "send-otp/",
        views.send_otp_test,
        name="send_otp"
    ),

    path(
        "verify-otp/",
        views.verify_otp,
        name="verify_otp"
    ),

    # Wishlist
    path(
        "wishlist/",
        views.wishlist,
        name="wishlist"
    ),

    path(
        "add-to-wishlist/<int:product_id>/",
        views.add_to_wishlist,
        name="add_to_wishlist"
    ),

    path(
        "remove-from-wishlist/<int:product_id>/",
        views.remove_from_wishlist,
        name="remove_from_wishlist"
    ),
    path(
    "google-success/",
    views.google_success,
    name="google_success"
    ),
    path(
        "profile/",
        views.profile,
        name="profile"
    ),

    path(
        "profile/edit/",
        views.edit_profile,
        name="edit_profile"
    ),

    path(
        "address/add/",
        views.add_address,
        name="add_address"
    ),

    path(
        "address/edit/<int:address_id>/",
        views.edit_address,
        name="edit_address"
    ),

    path(
        "address/delete/<int:address_id>/",
        views.delete_address,
        name="delete_address"
    ),

    # Forgot Password Flow
    path(
        "forgot-password/",
        views.forgot_password,
        name="forgot_password"
    ),

    path(
        "forgot-password/verify/",
        views.forgot_password_verify_otp,
        name="forgot_password_verify_otp"
    ),

    path(
        "reset-password/",
        views.reset_password,
        name="reset_password"
    ),
]