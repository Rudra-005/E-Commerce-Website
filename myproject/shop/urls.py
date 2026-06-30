from django.urls import path
from . import views

urlpatterns = [

    # Home
    path(
        "",
        views.HomeView.as_view(),
        name="home"
    ),

    # Product Detail
    path(
        "product/<int:product_id>/",
        views.ProductDetailView.as_view(),
        name="product_detail"
    ),

    # Search
    path(
        "search-suggestions/",
        views.SearchSuggestionsView.as_view(),
        name="search_suggestions"
    ),

    # Dedicated Products List Page
    path(
        "products/",
        views.ProductListView.as_view(),
        name="products_list"
    ),

    # Cart
    path(
        "cart/",
        views.CartView.as_view(),
        name="cart"
    ),

    path(
        "add-to-cart/<int:product_id>/",
        views.AddToCartView.as_view(),
        name="add_to_cart"
    ),

    path(
        "remove-from-cart/<int:product_id>/",
        views.RemoveFromCartView.as_view(),
        name="remove_from_cart"
    ),

    path(
        "increase-quantity/<int:product_id>/",
        views.IncreaseQuantityView.as_view(),
        name="increase_quantity"
    ),

    path(
        "decrease-quantity/<int:product_id>/",
        views.DecreaseQuantityView.as_view(),
        name="decrease_quantity"
    ),

    path(
        "clear-cart/",
        views.ClearCartView.as_view(),
        name="clear_cart"
    ),

    # Checkout
    path(
        "checkout/",
        views.CheckoutView.as_view(),
        name="checkout"
    ),

    # Verify Payment
    path(
        "verify-payment/",
        views.VerifyPaymentView.as_view(),
        name="verify_payment"
    ),

    # Order Confirmation
    path(
        "order-confirmation/<int:order_id>/",
        views.OrderConfirmationView.as_view(),
        name="order_confirmation"
    ),

    # Orders History
    path(
        "orders/",
        views.OrdersView.as_view(),
        name="orders"
    ),

    path(
        "order/<int:order_id>/request-refund/",
        views.RequestRefundView.as_view(),
        name="request_refund"
    ),

    # Stock Notification
    path(
        "notify-stock/<int:product_id>/",
        views.NotifyStockView.as_view(),
        name="notify_stock"
    ),

    # Login
    path(
        "login/",
        views.LoginView.as_view(),
        name="login"
    ),

    # Signup
    path(
        "signup/",
        views.SignupView.as_view(),
        name="signup"
    ),

    path(
        "logout/",
        views.LogoutView.as_view(),
        name="logout"
    ),

    # OTP
    path(
        "send-otp/",
        views.SendOTPTestView.as_view(),
        name="send_otp"
    ),

    path(
        "verify-otp/",
        views.VerifyOTPView.as_view(),
        name="verify_otp"
    ),

    # Wishlist
    path(
        "wishlist/",
        views.WishlistView.as_view(),
        name="wishlist"
    ),

    path(
        "add-to-wishlist/<int:product_id>/",
        views.AddToWishlistView.as_view(),
        name="add_to_wishlist"
    ),

    path(
        "remove-from-wishlist/<int:product_id>/",
        views.RemoveFromWishlistView.as_view(),
        name="remove_from_wishlist"
    ),

    path(
        "google-success/",
        views.GoogleSuccessView.as_view(),
        name="google_success"
    ),

    path(
        "addresses/",
        views.AddressesView.as_view(),
        name="addresses"
    ),

    path(
        "profile/",
        views.ProfileView.as_view(),
        name="profile"
    ),

    path(
        "profile/edit/",
        views.EditProfileView.as_view(),
        name="edit_profile"
    ),

    path(
        "address/add/",
        views.AddAddressView.as_view(),
        name="add_address"
    ),

    path(
        "address/edit/<int:address_id>/",
        views.EditAddressView.as_view(),
        name="edit_address"
    ),

    path(
        "address/delete/<int:address_id>/",
        views.DeleteAddressView.as_view(),
        name="delete_address"
    ),

    path(
        "address/set-default/<int:address_id>/",
        views.SetDefaultAddressView.as_view(),
        name="set_default_address"
    ),

    # Forgot Password Flow
    path(
        "forgot-password/",
        views.ForgotPasswordView.as_view(),
        name="forgot_password"
    ),

    path(
        "forgot-password/verify/",
        views.ForgotPasswordVerifyOTPView.as_view(),
        name="forgot_password_verify_otp"
    ),

    path(
        "reset-password/",
        views.ResetPasswordView.as_view(),
        name="reset_password"
    ),

    # Recommendations API
    path(
        "api/recommendations/",
        views.RecommendationAPIView.as_view(),
        name="api_recommendations"
    ),
]