from django.urls import path
from . import views
from . import views_admin
from . import views_support_api
from . import views_cancellations
from . import views_invoice
from . import views_subscription

urlpatterns = [
    # Invoices
    path('orders/<int:order_id>/invoice/view/', views_invoice.InvoiceView.as_view(), name='invoice_view'),
    path('orders/<int:order_id>/invoice/download/', views_invoice.InvoiceDownloadView.as_view(), name='invoice_download'),

    # Admin Panel
    path('admin/', views_admin.AdminBaseRedirectView.as_view(), name='admin_base_redirect'),
    path('admin/dashboard/', views_admin.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/chat/', views_admin.AdminChatView.as_view(), name='admin_chat'),
    path('admin/orders/', views_admin.AdminOrdersView.as_view(), name='admin_orders'),
    path('admin/products/', views_admin.AdminProductsView.as_view(), name='admin_products'),
    path('admin/users/', views_admin.AdminUsersView.as_view(), name='admin_users'),
    path('admin/analytics/', views_admin.AdminAnalyticsView.as_view(), name='admin_analytics'),
    path('admin/refunds/', views_admin.AdminRefundsView.as_view(), name='admin_refunds'),
    path('admin/refunds/process/', views_admin.AdminProcessRefundAPIView.as_view(), name='admin_process_refund'),
    path('admin/settings/', views_admin.AdminSettingsView.as_view(), name='admin_settings'),
    path('admin/email-campaigns/', views_admin.AdminEmailCampaignsView.as_view(), name='admin_email_campaigns'),
    
    # Support APIs
    path('api/support/admin/conversations/', views_support_api.AdminConversationsAPIView.as_view(), name='api_admin_conversations'),
    path('api/support/customer/conversation/', views_support_api.CustomerConversationAPIView.as_view(), name='api_customer_conversation'),
    path('api/support/conversation/<int:conversation_id>/messages/', views_support_api.ConversationMessagesAPIView.as_view(), name='api_conversation_messages'),
    path('api/support/upload_image/', views_support_api.UploadChatImageAPIView.as_view(), name='api_upload_chat_image'),

    # Order Cancellations
    path('api/orders/<int:order_id>/items/<int:item_id>/cancel/', views_cancellations.CancelOrderItemAPIView.as_view(), name='api_cancel_order_item'),
    path('admin/cancellations/', views_cancellations.AdminCancellationsView.as_view(), name='admin_cancellations'),
    path('api/admin/cancellations/<int:cancel_id>/process/', views_cancellations.AdminProcessCancellationAPIView.as_view(), name='api_admin_process_cancellation'),

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

    path(
        "api/checkout/validate_cod/",
        views.ValidateCODView.as_view(),
        name="validate_cod"
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

    # Subscriptions
    path(
        "membership/",
        views_subscription.MembershipView.as_view(),
        name="membership"
    ),
    path(
        "api/subscription/subscribe/",
        views_subscription.SubscribeAPIView.as_view(),
        name="api_subscribe"
    ),
    path(
        "api/subscription/manage/",
        views_subscription.ManageSubscriptionAPIView.as_view(),
        name="api_manage_subscription"
    ),
    path(
        "api/webhooks/razorpay/",
        views_subscription.RazorpayWebhookView.as_view(),
        name="api_razorpay_webhook"
    ),
]