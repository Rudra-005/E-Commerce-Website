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
    
    # Razorpay Payment Fields
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)

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
    
    # Addresses (Snapshot at time of order)
    billing_address = models.TextField()
    shipping_address = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice {self.invoice_number} for Order #{self.order.id}"
