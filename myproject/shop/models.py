from django.db import models


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

    customer_name = models.CharField(
        max_length=100
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    rating = models.IntegerField(
        default=5
    )

    title = models.CharField(
        max_length=200,
        blank=True
    )

    review_text = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    is_verified_purchase = models.BooleanField(
        default=False
    )

    helpful_count = models.IntegerField(
        default=0
    )

    class Meta:

        ordering = ["-created_at"]

    def __str__(self):

        return (
            f"{self.customer_name} "
            f"({self.rating}⭐) - "
            f"{self.product.name}"
        )