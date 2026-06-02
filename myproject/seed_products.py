import os
import django
import random

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "myproject.settings"
)

django.setup()

from shop.models import Product

# DELETE OLD PRODUCTS
Product.objects.all().delete()

# =========================================
# CATEGORY DATA
# =========================================

categories = {

    "Laptop": {
        "brands": [
            "Dell", "HP", "Lenovo", "Asus",
            "Acer", "MSI", "Samsung",
            "Apple", "LG", "Huawei"
        ],

        "types": [
            "Gaming", "Business", "Slim",
            "Notebook", "Ultra", "Professional"
        ],

        "extras": [
            "Intel i5",
            "Intel i7",
            "Intel i9",
            "Ryzen 5",
            "Ryzen 7",
            "Apple M2"
        ],

        "images": [
            "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=1200",
            "https://images.unsplash.com/photo-1517336714739-489689fd1ca8?w=1200",
            "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200",
            "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1200",
            "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=1200"
        ],

        "price": (45000, 250000)
    },

    "Mobile": {
        "brands": [
            "Apple", "Samsung", "OnePlus",
            "Xiaomi", "Realme", "Oppo",
            "Vivo", "Motorola"
        ],

        "types": [
            "Pro", "Ultra", "Max",
            "Plus", "Note", "5G"
        ],

        "extras": [
            "128GB",
            "256GB",
            "512GB",
            "8GB RAM",
            "12GB RAM"
        ],

        "images": [
            "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=1200",
            "https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?w=1200",
            "https://images.unsplash.com/photo-1580910051074-3eb694886505?w=1200"
        ],

        "price": (15000, 120000)
    },

    "Headphones": {
        "brands": [
            "Sony", "Boat", "JBL",
            "Bose", "Apple", "Noise"
        ],

        "types": [
            "Wireless",
            "Gaming",
            "Noise Cancelling",
            "Bluetooth"
        ],

        "extras": [
            "Bass Boost",
            "RGB",
            "ANC",
            "Premium"
        ],

        "images": [
            "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=1200",
            "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=1200"
        ],

        "price": (1500, 30000)
    },

    "Shoes": {
        "brands": [
            "Nike", "Adidas",
            "Puma", "Reebok",
            "Skechers"
        ],

        "types": [
            "Running",
            "Sports",
            "Casual",
            "Sneakers"
        ],

        "extras": [
            "Men",
            "Women",
            "Premium",
            "Comfort"
        ],

        "images": [
            "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=1200",
            "https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?w=1200",
            "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=1200"
        ],

        "price": (2000, 15000)
    },

    "Watch": {
        "brands": [
            "Apple", "Samsung",
            "Boat", "Noise",
            "Fastrack"
        ],

        "types": [
            "Smart",
            "Fitness",
            "Sports",
            "Classic"
        ],

        "extras": [
            "AMOLED",
            "Bluetooth",
            "Premium",
            "Waterproof"
        ],

        "images": [
            "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=1200",
            "https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?w=1200"
        ],

        "price": (3000, 50000)
    },

    "Speaker": {
        "brands": [
            "JBL", "Boat",
            "Sony", "Marshall"
        ],

        "types": [
            "Bluetooth",
            "Portable",
            "Party",
            "Wireless"
        ],

        "extras": [
            "Bass",
            "RGB",
            "Mini",
            "Premium"
        ],

        "images": [
            "https://images.unsplash.com/photo-1589003077984-894e133dabab?w=1200",
            "https://images.unsplash.com/photo-1545454675-3531b543be5d?w=1200"
        ],

        "price": (2000, 25000)
    },

    "Camera": {
        "brands": [
            "Canon",
            "Sony",
            "Nikon",
            "Fujifilm"
        ],

        "types": [
            "DSLR",
            "Mirrorless",
            "Professional",
            "4K"
        ],

        "extras": [
            "Lens Kit",
            "Premium",
            "Photography",
            "Video"
        ],

        "images": [
            "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=1200",
            "https://images.unsplash.com/photo-1502920917128-1aa500764ce7?w=1200"
        ],

        "price": (25000, 300000)
    },

    "TV": {
        "brands": [
            "Samsung",
            "LG",
            "Sony",
            "Xiaomi"
        ],

        "types": [
            "Smart",
            "OLED",
            "4K",
            "Ultra HD"
        ],

        "extras": [
            "55 Inch",
            "65 Inch",
            "Android",
            "Premium"
        ],

        "images": [
            "https://images.unsplash.com/photo-1593784991095-a205069470b6?w=1200",
            "https://images.unsplash.com/photo-1461151304267-38535e780c79?w=1200"
        ],

        "price": (25000, 180000)
    },

    "Keyboard": {
        "brands": [
            "Logitech",
            "Redragon",
            "HP",
            "Dell"
        ],

        "types": [
            "Mechanical",
            "Gaming",
            "Wireless",
            "RGB"
        ],

        "extras": [
            "Blue Switch",
            "Premium",
            "Compact",
            "Fast"
        ],

        "images": [
            "https://images.unsplash.com/photo-1511467687858-23d96c32e4ae?w=1200"
        ],

        "price": (1000, 12000)
    },

    "Mouse": {
        "brands": [
            "Logitech",
            "HP",
            "Dell",
            "Razer"
        ],

        "types": [
            "Gaming",
            "Wireless",
            "RGB",
            "Bluetooth"
        ],

        "extras": [
            "Fast",
            "Ergonomic",
            "Premium",
            "Rechargeable"
        ],

        "images": [
            "https://images.unsplash.com/photo-1527814050087-3793815479db?w=1200"
        ],

        "price": (500, 10000)
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

        name = f"{brand} {type_name} {category_name} {extra}"

        description = (
            f"{brand} {category_name} with premium quality. "
            f"Perfect for gaming, office work, entertainment and daily usage."
        )

        price = random.randint(
            data["price"][0],
            data["price"][1]
        )

        Product.objects.create(

            name=name,

            price=price,

            image=random.choice(data["images"]),

            description=description,

            category=category_name,

            stock=random.randint(5, 100)
        )

        print(f"{name} Added")

print("ALL PRODUCTS ADDED SUCCESSFULLY")