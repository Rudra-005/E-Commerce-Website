import os
import django
import random

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "myproject.settings"
)

django.setup()

from shop.models import Product, Category

# =========================================
# NEW CATEGORY DATA (5 empty categories)
# =========================================

categories = {

    "Electronics": {
        "brands": [
            "Philips", "Havells", "Bajaj",
            "Crompton", "Orient", "Syska",
            "Usha", "Panasonic", "Bosch", "LG"
        ],

        "types": [
            "Smart Plug", "LED Bulb", "Power Strip",
            "Extension Board", "Charger", "Adapter",
            "Cable", "Battery Pack", "Voltage Stabilizer"
        ],

        "extras": [
            "WiFi Enabled",
            "Fast Charging",
            "Energy Saver",
            "Premium",
            "Heavy Duty",
            "Compact"
        ],

        "images": [
            "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200",
            "https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=1200",
            "https://images.unsplash.com/photo-1588508065123-287b28e013da?w=1200",
            "https://images.unsplash.com/photo-1606229365485-93a3b8ee0385?w=1200"
        ],

        "price": (500, 15000)
    },

    "Fashion": {
        "brands": [
            "Levi's", "H&M", "Zara",
            "Allen Solly", "Peter England",
            "Van Heusen", "Raymond", "UCB"
        ],

        "types": [
            "T-Shirt", "Shirt", "Jeans",
            "Jacket", "Hoodie", "Kurta",
            "Dress", "Blazer"
        ],

        "extras": [
            "Slim Fit",
            "Regular Fit",
            "Cotton",
            "Premium",
            "Casual",
            "Formal"
        ],

        "images": [
            "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1200",
            "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=1200",
            "https://images.unsplash.com/photo-1558171813-4c088753af8f?w=1200",
            "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=1200",
            "https://images.unsplash.com/photo-1434389677669-e08b4cda3a2b?w=1200"
        ],

        "price": (500, 8000)
    },

    "Books": {
        "brands": [
            "Penguin", "HarperCollins", "Scholastic",
            "Oxford", "Pearson", "McGraw Hill",
            "Arihant", "S. Chand"
        ],

        "types": [
            "Novel", "Textbook", "Self-Help",
            "Biography", "Science Fiction", "Thriller",
            "Mystery", "Programming Guide"
        ],

        "extras": [
            "Bestseller",
            "Paperback",
            "Hardcover",
            "Limited Edition",
            "New Release",
            "Classic"
        ],

        "images": [
            "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=1200",
            "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=1200",
            "https://images.unsplash.com/photo-1524578271613-d550eacf6090?w=1200",
            "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=1200"
        ],

        "price": (200, 3000)
    },

    "Home": {
        "brands": [
            "IKEA", "HomeTown", "Godrej",
            "Nilkamal", "Urban Ladder",
            "Pepperfry", "Wipro", "Philips"
        ],

        "types": [
            "Table Lamp", "Wall Clock", "Cushion Cover",
            "Bed Sheet", "Curtain", "Storage Box",
            "Organizer", "Decor Set"
        ],

        "extras": [
            "Modern",
            "Vintage",
            "Minimalist",
            "Premium",
            "Handcrafted",
            "Eco-Friendly"
        ],

        "images": [
            "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=1200",
            "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=1200",
            "https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=1200",
            "https://images.unsplash.com/photo-1505691938895-1758d7feb511?w=1200"
        ],

        "price": (500, 12000)
    },

    "Sports": {
        "brands": [
            "Nike", "Adidas", "Puma",
            "Yonex", "Cosco", "Nivia",
            "SG", "SS", "Spartan"
        ],

        "types": [
            "Cricket Bat", "Football", "Badminton Racket",
            "Yoga Mat", "Dumbbell Set", "Resistance Band",
            "Skipping Rope", "Boxing Gloves"
        ],

        "extras": [
            "Professional",
            "Training",
            "Beginner",
            "Premium",
            "Lightweight",
            "Competition Grade"
        ],

        "images": [
            "https://images.unsplash.com/photo-1461896836934-bd45ba8c3e7f?w=1200",
            "https://images.unsplash.com/photo-1517649763962-0c623066013b?w=1200",
            "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=1200",
            "https://images.unsplash.com/photo-1599058917212-d750089bc07e?w=1200"
        ],

        "price": (500, 25000)
    }

}

# =========================================
# CREATE 60 PRODUCTS PER CATEGORY
# =========================================

for category_name, data in categories.items():

    for i in range(60):

        brand = random.choice(data["brands"])

        type_name = random.choice(data["types"])

        extra = random.choice(data["extras"])

        name = f"{brand} {type_name} {extra}"

        description = (
            f"{brand} {type_name} - {extra}. "
            f"High quality {category_name.lower()} product perfect for everyday use."
        )

        price = random.randint(
            data["price"][0],
            data["price"][1]
        )

        category_obj = Category.objects.get(
            name=category_name
        )

        Product.objects.create(
            name=name,
            price=price,
            image=random.choice(data["images"]),
            description=description,

            category=category_name,

            category_fk=category_obj,

            stock=random.randint(5, 100)
        )

        print(f"{name} Added")

print(f"\nALL NEW CATEGORY PRODUCTS ADDED SUCCESSFULLY!")
print(f"Total new products: {60 * len(categories)}")
