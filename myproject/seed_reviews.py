import os
import django
import random

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "myproject.settings"
)

django.setup()

from shop.models import Product, Review

# =========================================
# ADD REVIEWS TO PRODUCTS WITH 0 REVIEWS
# =========================================

customer_names = [
    "Rahul Sharma", "Priya Singh", "Amit Kumar", "Sneha Patel",
    "Vikram Joshi", "Ananya Gupta", "Rohan Mehta", "Kavita Nair",
    "Deepak Verma", "Neha Agarwal", "Arjun Reddy", "Pooja Mishra",
    "Sanjay Kapoor", "Ritu Desai", "Karan Malhotra", "Divya Iyer",
    "Manish Tiwari", "Swati Chauhan", "Rajesh Pandey", "Isha Bansal",
    "Ankur Saxena", "Meera Jain", "Tushar Rathore", "Pallavi Dubey",
    "Suresh Yadav", "Nisha Bhatt", "Aakash Soni", "Shruti Kulkarni"
]

review_titles = {
    "Electronics": [
        "Great quality!", "Works perfectly", "Value for money",
        "Excellent build", "Highly recommended", "Solid product",
        "Must have gadget", "Very useful", "Good purchase"
    ],
    "Fashion": [
        "Perfect fit!", "Love the fabric", "Stylish and comfortable",
        "Great quality material", "Looks amazing", "Worth every penny",
        "Super trendy", "Feels premium", "Excellent stitching"
    ],
    "Books": [
        "Must read!", "Couldn't put it down", "Very informative",
        "Excellent writing", "Great for learning", "Page turner",
        "Highly educational", "Beautiful print quality", "Amazing content"
    ],
    "Home": [
        "Beautiful decor!", "Perfect for home", "Great quality",
        "Looks elegant", "Very durable", "Amazing craftsmanship",
        "Love the design", "Perfect gift", "Matches my room"
    ],
    "Sports": [
        "Great for training!", "Excellent grip", "Very durable",
        "Professional quality", "Perfect for beginners", "Solid build",
        "Lightweight and strong", "Best in class", "Worth the price"
    ]
}

review_texts = {
    "Electronics": [
        "This product exceeded my expectations. Works flawlessly with all my devices. The build quality is top-notch and it feels very durable.",
        "Bought this for daily use and I'm very satisfied. Easy to set up and the performance is consistent. Definitely worth the investment.",
        "Great electronic gadget! The quality is amazing for the price. It performs well under heavy usage and the design is sleek.",
        "Very happy with this purchase. It's energy efficient and works exactly as described. The packaging was also very secure.",
        "Excellent product with premium build quality. I've been using it for weeks now and it hasn't disappointed me at all."
    ],
    "Fashion": [
        "The fabric quality is exceptional. Fits perfectly and looks great. I received many compliments wearing this. Will definitely buy more.",
        "Absolutely love this piece! The stitching is neat and the material feels premium. True to size and very comfortable for all-day wear.",
        "Amazing fashion piece. The color is exactly as shown in the pictures. Very comfortable and breathable fabric. Great value for money.",
        "This is now my favorite outfit! The design is trendy and the fit is perfect. Washed it multiple times and the color hasn't faded.",
        "Wonderful quality clothing. The material is soft and comfortable. Perfect for both casual outings and semi-formal occasions."
    ],
    "Books": [
        "An absolute masterpiece! The content is well-structured and engaging. Kept me hooked from the first page to the last. Highly recommended.",
        "This book is incredibly informative and well-written. The author has done a fantastic job explaining complex topics in simple language.",
        "One of the best books I've read this year. The print quality is excellent and the binding is sturdy. A must-have for every bookshelf.",
        "Thoroughly enjoyed reading this. The narrative is gripping and the characters are well-developed. Perfect for weekend reading sessions.",
        "Great investment in knowledge. The content is comprehensive and up-to-date. Very helpful for both beginners and advanced readers."
    ],
    "Home": [
        "This product transformed my living space! The quality is outstanding and it looks much more expensive than it actually is. Love it!",
        "Beautiful addition to my home. The craftsmanship is excellent and the materials feel premium. It matches perfectly with my existing decor.",
        "Very impressed with the quality. Easy to set up and it looks absolutely stunning. Received many compliments from guests who visited.",
        "Perfect home accessory. The design is modern and elegant. The durability is remarkable - it still looks brand new after months of use.",
        "Exactly what I was looking for! The finish is smooth and the color is beautiful. It adds a touch of sophistication to any room."
    ],
    "Sports": [
        "Excellent sports equipment! Perfect for my daily workout routine. The build quality is professional grade and it feels very sturdy.",
        "Great quality product. I've been using it for training sessions and it holds up perfectly. Very comfortable grip and lightweight design.",
        "This is a game-changer for my fitness routine! The material quality is top-notch and it's very durable even with heavy daily use.",
        "Perfect for both beginners and professionals. The quality matches products that cost twice as much. Very happy with this purchase.",
        "Superb product for sports enthusiasts. The design is ergonomic and the performance is outstanding. Highly recommend for serious athletes."
    ]
}

# Get products without reviews
products_without_reviews = Product.objects.filter(reviews__isnull=True)
print(f"Found {products_without_reviews.count()} products without reviews")

count = 0
for product in products_without_reviews:
    cat_name = product.category
    
    # Each product gets 5-15 random reviews
    num_reviews = random.randint(5, 15)
    
    titles = review_titles.get(cat_name, review_titles["Electronics"])
    texts = review_texts.get(cat_name, review_texts["Electronics"])
    
    for _ in range(num_reviews):
        # Weighted ratings: more 4s and 5s (realistic distribution)
        rating = random.choices(
            [1, 2, 3, 4, 5],
            weights=[3, 5, 10, 30, 52],
            k=1
        )[0]
        
        Review.objects.create(
            product=product,
            customer_name=random.choice(customer_names),
            email=f"{random.choice(customer_names).split()[0].lower()}{random.randint(1,999)}@gmail.com",
            rating=rating,
            title=random.choice(titles),
            review_text=random.choice(texts),
            is_verified_purchase=random.choice([True, True, True, False]),
            helpful_count=random.randint(0, 50)
        )
    
    count += 1
    if count % 30 == 0:
        print(f"  Added reviews for {count} products...")

print(f"\nDone! Added reviews for {count} products")
print(f"Total reviews now: {Review.objects.count()}")