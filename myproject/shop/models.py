from django.db import models 
from django.contrib.auth.models import User



class Category(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    slug = models.SlugField(
        unique=True
    )

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):

    name = models.CharField(max_length=200)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    image = models.URLField()

    description = models.TextField()

    category = models.CharField(
        max_length=100
    )

    # NEW FIELD
    category_fk = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="products"
    )

    stock = models.IntegerField(
        default=0
    )

    early_access_only = models.BooleanField(
        default=False,
        help_text="Only available for premium members"
    )

    # Added for analytics background task
    popularity_score = models.FloatField(
        default=0.0
    )


    @property
    def average_rating(self):

        reviews = self.reviews.all()

        if not reviews.exists():
            return 0

        return round(

            sum(
                review.rating
                for review in reviews
            ) / reviews.count(),

            1
        )

    @property
    def total_reviews(self):

        return self.reviews.count()

    def __str__(self):
        return self.name


class Review(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    customer_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    rating = models.IntegerField(default=5)
    title = models.CharField(max_length=200, blank=True)
    review_text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_verified_purchase = models.BooleanField(default=False)

    helpful_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.customer_name} "
            f"({self.rating}⭐) - "
            f"{self.product.name}"
        )


class Cart(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    # Added for checkout expiration and guest cart cleanup
    session_key = models.CharField(max_length=40, blank=True, null=True)
    status = models.CharField(max_length=20, default="ACTIVE")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    @property
    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return self.product.name


class EmailOTP(models.Model):

    email = models.EmailField()

    otp = models.CharField(
        max_length=6
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.email

class ProductCollection(models.Model):
    name = models.CharField(max_length=100)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='collections')

    def __str__(self):
        return f"{self.name} - {self.product.name}"

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlists")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username}'s wishlist: {self.product.name}"


class UserProfile(models.Model):

    AVATAR_CHOICES = [
        ('ninja', '🥷'),
        ('alien', '👽'),
        ('robot', '🤖'),
        ('ghost', '👻'),
        ('wizard', '🧙'),
        ('astronaut', '🧑‍🚀'),
        ('cat', '😺'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    phone = models.CharField(
        max_length=15,
        blank=True
    )

    profile_image = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True
    )

    avatar = models.CharField(
        max_length=20,
        choices=AVATAR_CHOICES,
        default='ninja',
        blank=True
    )

    date_of_birth = models.DateField(
        blank=True,
        null=True
    )

    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('support', 'Support'),
        ('admin', 'Admin'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='customer'
    )

    permissions = models.JSONField(
        default=list,
        blank=True
    )

    @property
    def display_avatar(self):
        """Returns the emoji for the selected avatar."""
        avatar_map = dict(self.AVATAR_CHOICES)
        return avatar_map.get(self.avatar, '🥷')

    def __str__(self):
        return self.user.username


class Address(models.Model):

    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="addresses"
    )

    full_name = models.CharField(
        max_length=100,
        default=""
    )

    phone = models.CharField(
        max_length=15,
        default=""
    )

    address_line_1 = models.CharField(
        max_length=255,
        default=""
    )

    address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    city = models.CharField(
        max_length=100,
        default=""
    )

    state = models.CharField(
        max_length=100,
        default=""
    )

    pincode = models.CharField(
        max_length=10,
        default=""
    )

    is_default = models.BooleanField(
        default=False
    )

    class Meta:
        verbose_name_plural = "Addresses"

    def __str__(self):
        return self.full_name


class ShippingAddress(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="shipping_addresses"
    )
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    class Meta:
        verbose_name_plural = "Shipping Addresses"

    def __str__(self):
        return f"{self.full_name} - {self.city}"


class Order(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders"
    )
    shipping_address = models.ForeignKey(
        ShippingAddress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default="Pending")
    
    # Payment Fields
    payment_method = models.CharField(max_length=50, default="Online")
    payment_status = models.CharField(max_length=50, default="Pending")
    cod_verified = models.BooleanField(default=False)
    
    # Razorpay Payment Fields
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)

    # Subscription Tracking
    subscription_used = models.BooleanField(default=False)
    membership_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    @property
    def get_refund(self):
        try:
            return self.refund_request
        except Exception:
            return None

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default="Pending")

    @property
    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.product.name} x {self.quantity} ({self.status})"



class UserInteraction(models.Model):
    INTERACTION_CHOICES = (
        ('view', 'View'),
        ('wishlist', 'Wishlist'),
        ('cart', 'Cart'),
        ('purchase', 'Purchase'),
        ('review', 'Review'),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="interactions"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="interactions"
    )
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_CHOICES
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.interaction_type} - {self.product.name}"


class StockNotification(models.Model):
    """Track users who want to be notified when a product is back in stock."""
    email = models.EmailField()
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_notifications"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)

    class Meta:
        unique_together = ('email', 'product')

    def __str__(self):
        return f"{self.email} → {self.product.name}"


class RefundRequest(models.Model):
    REFUND_STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="refund_request"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="refund_requests"
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=REFUND_STATUS_CHOICES,
        default='Pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def get_transaction(self):
        try:
            return self.transaction
        except Exception:
            return None

    def __str__(self):
        return f"Refund #{self.id} for Order #{self.order.id} - {self.status}"


class RefundTransaction(models.Model):
    TRANSACTION_STATUS_CHOICES = (
        ('Processing', 'Processing'),
        ('Success', 'Success'),
        ('Failed', 'Failed'),
    )

    refund_request = models.OneToOneField(
        RefundRequest,
        on_delete=models.CASCADE,
        related_name="transaction"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=TRANSACTION_STATUS_CHOICES,
        default='Processing'
    )
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction for Refund #{self.refund_request.id} - {self.status}"


class OrderItemCancellation(models.Model):
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="cancellations"
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="item_cancellations"
    )
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="item_cancellations"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    quantity_cancelled = models.PositiveIntegerField()
    reason = models.CharField(max_length=100)
    other_reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default="Pending")
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    refund_status = models.CharField(max_length=50, default="Pending")
    refund_reference = models.CharField(max_length=100, blank=True, null=True)
    refund_completed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_cancellations"
    )
    admin_notes = models.TextField(blank=True, null=True)
    is_partial_cancel = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cancel {self.product.name} (Order #{self.order.id}) - {self.status}"


class SupportConversation(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="support_conversations")
    assigned_admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_conversations")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='low')
    last_message = models.TextField(blank=True)
    last_message_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation #{self.id} with {self.customer.username}"

class SupportMessage(models.Model):
    SENDER_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    )
    MESSAGE_TYPE_CHOICES = (
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
    )

    conversation = models.ForeignKey(SupportConversation, on_delete=models.CASCADE, related_name="messages")
    sender_id = models.IntegerField()
    sender_type = models.CharField(max_length=20, choices=SENDER_TYPE_CHOICES)
    message = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message in #{self.conversation.id} by {self.sender_type}"


class Invoice(models.Model):
    invoice_number = models.CharField(max_length=50, unique=True)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices')
    invoice_pdf = models.FileField(upload_to='invoices/', blank=True, null=True)
    
    # Financial fields
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    
    # Payment fields
    payment_method = models.CharField(max_length=50, default="Razorpay")
    payment_status = models.CharField(max_length=50, default="Paid")
    gst_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Subscription Tracking
    subscription_used = models.BooleanField(default=False)
    membership_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Addresses (Snapshot at time of order)
    billing_address = models.TextField()
    shipping_address = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice {self.invoice_number} for Order #{self.order.id}"

class TaskExecutionLog(models.Model):
    task_name = models.CharField(max_length=255)
    queue_name = models.CharField(max_length=100)
    status = models.CharField(max_length=50, default='PENDING')
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    execution_time = models.FloatField(null=True, blank=True, help_text="Execution time in seconds")
    retry_count = models.IntegerField(default=0)
    exception = models.TextField(null=True, blank=True)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task_name} ({self.status})"

class AIEmailCampaign(models.Model):
    topic = models.CharField(max_length=255)
    languages = models.CharField(max_length=255, default='English, Hindi, Spanish, French', help_text="Comma-separated list of languages")
    schedule_value = models.IntegerField(default=1, help_text="Interval value")
    schedule_unit = models.CharField(max_length=20, default='Minutes', help_text="Interval unit (Minutes, Hours, Days, Weeks)")
    is_active = models.BooleanField(default=True)
    current_language_index = models.IntegerField(default=0)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Campaign on: {self.topic} ({'Active' if self.is_active else 'Inactive'})"

class AIEmailLog(models.Model):
    campaign = models.ForeignKey(AIEmailCampaign, on_delete=models.CASCADE, related_name='logs')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    language = models.CharField(max_length=50)
    recipient_count = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='SENT')
    exception = models.TextField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.campaign.topic} - {self.language} ({self.status})"

# ==========================================
# Subscription System Models
# ==========================================

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    razorpay_plan_id = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(
        max_length=20,
        choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')]
    )
    
    # Benefits
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    free_delivery = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    early_access = models.BooleanField(default=False)
    premium_access = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class UserSubscription(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('PENDING', 'Pending'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
        ('PAUSED', 'Paused'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    subscription_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    
    razorpay_subscription_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    razorpay_customer_id = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    
    auto_renew = models.BooleanField(default=True)
    cancel_at_cycle_end = models.BooleanField(default=False)
    
    payment_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.subscription_plan.name} ({self.status})"

# ==========================================
# Task-specific Models (Coupon & Notification)
# ==========================================

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.discount_percentage}%)"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    archived = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.username}"

# ==========================================
# Inventory Transactions
# ==========================================

class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('RESERVED', 'Reserved'),
        ('COMMITTED', 'Committed'),
        ('RELEASED', 'Released'),
        ('RESTOCKED', 'Restocked'),
    ]

    reference_id = models.CharField(max_length=100, help_text="Order ID or Cart ID")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_transactions')
    quantity = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    idempotency_key = models.CharField(max_length=255, unique=True, help_text="Ensures idempotent operations")
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_type} {self.quantity} of {self.product.name} ({self.reference_id})"