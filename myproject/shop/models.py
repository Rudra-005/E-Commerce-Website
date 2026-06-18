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
    
    from django.contrib.auth.models import User

class UserProfile(models.Model):

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

    date_of_birth = models.DateField(
        blank=True,
        null=True
    )

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

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"