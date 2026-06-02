import os
import django
import random

from faker import Faker

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "myproject.settings"
)

django.setup()

from shop.models import Product, Review

fake = Faker()

products = Product.objects.all()

reviews_created = 0

for product in products:

    total_reviews = random.randint(
        5,
        20
    )

    for _ in range(total_reviews):

        rating = random.randint(
            1,
            5
        )

        # Rating-wise titles

        if rating == 5:

            title = random.choice([

                "Excellent Product",
                "Highly Recommended",
                "Amazing Product",
                "Loved It",
                "Best Purchase Ever",
                "Outstanding Quality",
                "Perfect Product"

            ])

        elif rating == 4:

            title = random.choice([

                "Very Good Product",
                "Worth Buying",
                "Good Quality",
                "Satisfied Customer",
                "Value For Money",
                "Premium Feel"

            ])

        elif rating == 3:

            title = random.choice([

                "Average Product",
                "Decent Purchase",
                "Okay Product",
                "Not Bad",
                "Fair Quality"

            ])

        elif rating == 2:

            title = random.choice([

                "Needs Improvement",
                "Could Be Better",
                "Below Expectations",
                "Not As Expected"

            ])

        else:

            title = random.choice([

                "Poor Quality",
                "Not Recommended",
                "Waste Of Money",
                "Bad Experience",
                "Disappointed"

            ])

        Review.objects.create(

            product=product,

            customer_name=fake.name(),

            email=fake.email(),

            rating=rating,

            title=title,

            review_text=fake.paragraph(
                nb_sentences=5
            ),

            is_verified_purchase=random.choice(
                [True, False]
            ),

            helpful_count=random.randint(
                0,
                100
            )

        )

        reviews_created += 1

print(
    f"{reviews_created} reviews added successfully."
)