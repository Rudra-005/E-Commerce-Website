from urllib import request

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from flask import request
from django.core.paginator import Paginator
from django.db.models import Avg, Q
from .models import Product, Category, Review, Cart, EmailOTP, Wishlist
from django.contrib.postgres.search import TrigramSimilarity

from .decorators import jwt_login_required
from .models import UserProfile
from .models import Address

from django.contrib.auth import authenticate
from django.shortcuts import render, redirect

from .auth_helpers import generate_tokens

from .models import UserProfile
from .models import Address

from .decorators import jwt_login_required

def get_fuzzy_search_results(query_str, queryset, limit=None):
    query_str = query_str.strip()
    if not query_str:
        return list(queryset)

    queryset = queryset.annotate(
        similarity=TrigramSimilarity('name', query_str) + TrigramSimilarity('category', query_str)
    ).filter(similarity__gt=0.1).order_by('-similarity', '-id')

    matched_products = list(queryset)

    if limit:
        matched_products = matched_products[:limit]

    return matched_products

def sort_products_list(products_list, sort_by):
    if sort_by == "price_low":
        products_list.sort(key=lambda p: p.price)
    elif sort_by == "price_high":
        products_list.sort(key=lambda p: p.price, reverse=True)
    elif sort_by == "alphabet":
        products_list.sort(key=lambda p: p.name)
    elif sort_by == "alphabet_desc":
        products_list.sort(key=lambda p: p.name, reverse=True)
    elif sort_by in ["rating", "popular"]:
        products_list.sort(key=lambda p: p.average_rating or 0, reverse=True)
    else:
        products_list.sort(key=lambda p: p.id, reverse=True)
    return products_list

def home(request):

    search = request.GET.get("search", "").strip()
    #category = request.GET.get("category", "").strip()
    sort_by = request.GET.get("sort", "")
    page_number = request.GET.get("page", 1)

    featured_products = Product.objects.order_by("?")[:20]

    # BASE QUERYSET
    products_queryset = Product.objects.all()

    # COLLECTION FILTER
    collection_name = request.GET.get("collection")
    collection_title = ""
    if collection_name:
        products_queryset = products_queryset.filter(collections__name=collection_name).distinct()
        collection_title = collection_name.replace("-", " ").title()

    # CATEGORY FILTER
    category_id = request.GET.get("category")

    if category_id:
        if category_id.isdigit():
            products_queryset = products_queryset.filter(category_fk_id=category_id)
        else:
            products_queryset = products_queryset.filter(
                Q(category_fk__slug=category_id) | Q(category_fk__name=category_id)
            )

    # SEARCH & SORTING FILTER
    if search:
        matched_list = get_fuzzy_search_results(search, products_queryset)
        products_queryset = sort_products_list(matched_list, sort_by)
    else:
        # SORTING on QuerySet level
        if sort_by == "price_low":
            products_queryset = products_queryset.order_by("price")

        elif sort_by == "price_high":
            products_queryset = products_queryset.order_by("-price")

        elif sort_by == "alphabet":
            products_queryset = products_queryset.order_by("name")

        elif sort_by == "alphabet_desc":
            products_queryset = products_queryset.order_by("-name")

        elif sort_by == "rating":
            products_queryset = products_queryset.annotate(
                avg_rating=Avg("reviews__rating")
            ).order_by("-avg_rating")

        elif sort_by == "popular":
            products_queryset = products_queryset.annotate(
                avg_rating=Avg("reviews__rating")
            ).order_by("-avg_rating")

        else:
            products_queryset = products_queryset.order_by("-id")

    # PAGINATION
    paginator = Paginator(products_queryset, 12)
    products = paginator.get_page(page_number)

    # AJAX REQUEST
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":

        product_data = []

        for product in products:

            product_data.append({

                "id": product.id,
                "name": product.name,
                "price": str(product.price),
                "description": product.description,
                "image": product.image,
                "rating": product.average_rating,
                "reviews": product.total_reviews

            })

        return JsonResponse({

            "products": product_data,
            "has_next": products.has_next(),
            "current_page": products.number

        })

    categories = Category.objects.all()

    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist_product_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    context = {
        "products": products,
        "featured_products": featured_products,
        "categories": categories,
        "search": search,
        "selected_category": category_id,
        "category": category_id,
        "collection_name": collection_name,
        "collection_title": collection_title,
        "sort_by": sort_by,
        "wishlist_product_ids": wishlist_product_ids,
    }

    return render(
        request,
        "shop/home.html",
        context
    )

def products_list(request):
    search = request.GET.get("search", "").strip()
    category_id = request.GET.get("category", "").strip()
    collection_name = request.GET.get("collection", "").strip()
    sort_by = request.GET.get("sort", "")
    page_number = request.GET.get("page", 1)

    products_queryset = Product.objects.all()
    title = "All Products"

    # Collection Filter
    if collection_name:
        products_queryset = products_queryset.filter(collections__name=collection_name).distinct()
        title = collection_name.replace("-", " ").title()

    # Category Filter
    if category_id:
        if category_id.isdigit():
            category = get_object_or_404(Category, id=category_id)
        else:
            category = get_object_or_404(Category, Q(slug=category_id) | Q(name=category_id))
        products_queryset = products_queryset.filter(category_fk=category)
        title = category.name

    # Search & Sorting Filter
    if search:
        matched_list = get_fuzzy_search_results(search, products_queryset)
        products_queryset = sort_products_list(matched_list, sort_by)
    else:
        # SORTING on QuerySet level
        if sort_by == "price_low":
            products_queryset = products_queryset.order_by("price")
        elif sort_by == "price_high":
            products_queryset = products_queryset.order_by("-price")
        elif sort_by == "alphabet":
            products_queryset = products_queryset.order_by("name")
        elif sort_by == "alphabet_desc":
            products_queryset = products_queryset.order_by("-name")
        elif sort_by in ["rating", "popular"]:
            products_queryset = products_queryset.annotate(
                avg_rating=Avg("reviews__rating")
            ).order_by("-avg_rating")
        else:
            products_queryset = products_queryset.order_by("-id")

    # Pagination
    paginator = Paginator(products_queryset, 12)
    products = paginator.get_page(page_number)

    # AJAX Request
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        product_data = []
        for product in products:
            product_data.append({
                "id": product.id,
                "name": product.name,
                "price": str(product.price),
                "description": product.description,
                "image": product.image,
                "rating": product.average_rating,
                "reviews": product.total_reviews
            })
        return JsonResponse({
            "products": product_data,
            "has_next": products.has_next(),
            "current_page": products.number
        })

    categories = Category.objects.all()
    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist_product_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    context = {
        "products": products,
        "categories": categories,
        "search": search,
        "title": title,
        "selected_category": category_id,
        "category_id": category_id,
        "collection_name": collection_name,
        "sort_by": sort_by,
        "wishlist_product_ids": wishlist_product_ids,
    }

    return render(
        request,
        "shop/product_list.html",
        context
    )
# =====================================
# PRODUCT DETAIL + REVIEWS
# =====================================

def product_detail(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id
    )

    if request.method == "POST":

        Review.objects.create(

            product=product,

            customer_name=request.POST.get(
                "customer_name"
            ),

            email=request.POST.get(
                "email"
            ),

            rating=request.POST.get(
                "rating"
            ),

            title=request.POST.get(
                "title",
                ""
            ),

            review_text=request.POST.get(
                "review_text"
            )

        )

        return redirect(
            "product_detail",
            product_id=product.id
        )

    reviews_list = product.reviews.all().order_by("-id")
    from django.core.paginator import Paginator
    paginator = Paginator(reviews_list, 5)
    page_number = request.GET.get("page")
    reviews = paginator.get_page(page_number)

    related_products = Product.objects.exclude(
        id=product.id
    ).order_by("?")[:8]

    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist_product_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    return render(

        request,

        "shop/product_detail.html",

        {

            "product": product,

            "reviews": reviews,

            "related_products": related_products,

            "wishlist_product_ids": wishlist_product_ids

        }

    )

# =====================================
# SEARCH SUGGESTIONS
# =====================================

def search_suggestions(request):

    term = request.GET.get(
        "term",
        ""
    ).strip()

    if not term:
        return JsonResponse([], safe=False)

    all_products = Product.objects.all()
    matched_products = get_fuzzy_search_results(term, all_products, limit=10)

    data = []

    for product in matched_products:

        data.append({

            "id": product.id,

            "name": product.name,

            "price": str(product.price)

        })

    return JsonResponse(
        data,
        safe=False
    )


# =====================================
# CART FUNCTIONS
# =====================================



from django.contrib.auth.decorators import login_required
from .decorators import jwt_login_required

@jwt_login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    return redirect("cart")

@jwt_login_required
def cart(request):
    cart_items = Cart.objects.filter(user=request.user)
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render(
        request,
        "shop/cart.html",
        {
            "cart_items": cart_items,
            "total": total
        }
    )

@login_required(login_url="/login/")
def increase_quantity(request, product_id):
    item = get_object_or_404(Cart, user=request.user, product_id=product_id)
    item.quantity += 1
    item.save()
    return redirect("cart")

@login_required(login_url="/login/")
def decrease_quantity(request, product_id):
    item = get_object_or_404(Cart, user=request.user, product_id=product_id)
    item.quantity -= 1
    if item.quantity <= 0:
        item.delete()
    else:
        item.save()
    return redirect("cart")

@login_required(login_url="/login/")
def remove_from_cart(request, product_id):
    Cart.objects.filter(user=request.user, product_id=product_id).delete()
    return redirect("cart")

@login_required(login_url="/login/")
def clear_cart(request):
    Cart.objects.filter(user=request.user).delete()
    return redirect("cart")

def login_view(request):

    if request.method == "POST":

        username = request.POST.get(
            "username"
        )

        password = request.POST.get(
            "password"
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user:

            access_token, refresh_token = generate_tokens(
                user
            )

            response = redirect(
                "home"
            )

            response.set_cookie(
                "access_token",
                access_token,
                httponly=True,
                samesite="Lax"
            )

            response.set_cookie(
                "refresh_token",
                refresh_token,
                httponly=True,
                samesite="Lax"
            )

            return response

        return render(
            request,
            "shop/login.html",
            {
                "error": "Invalid Credentials"
            }
        )

    return render(
        request,
        "shop/login.html"
    )

from django.contrib.auth import authenticate, login

def login_page(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            return redirect("home")

        return render(
            request,
            "shop/login.html",
            {"error": "Invalid Credentials"}
        )

    return render(
        request,
        "shop/login.html"
    )


def signup_page(request):

    if request.method == "POST":
        from django.contrib.auth.models import User
        import random
        from django.core.mail import send_mail
        from django.conf import settings

        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            return render(
                request,
                "shop/signup.html",
                {"error": "Passwords do not match"}
            )
            
        if User.objects.filter(username=username).exists():
            return render(
                request,
                "shop/signup.html",
                {"error": "Username already exists. Choose another username."}
            )
            
        if User.objects.filter(email__iexact=email).exists():
            return render(
                request,
                "shop/signup.html",
                {"error": "An account with this email already exists."}
            )

        otp = str(random.randint(100000, 999999))

        EmailOTP.objects.filter(
            email=email
        ).delete()

        EmailOTP.objects.create(
            email=email,
            otp=otp
        )

        request.session["signup_username"] = username
        request.session["signup_email"] = email
        request.session["signup_password"] = password1

        send_mail(
            "Velora Email Verification",
            f"Your OTP is {otp}",
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        return redirect("verify_otp")

    return render(
        request,
        "shop/signup.html"
    )

# =====================================
# CHECKOUT
# =====================================

@jwt_login_required
def checkout_view(request):
    from .models import ShippingAddress, Order, OrderItem, Cart, Address, UserProfile
    
    # Retrieve active cart items
    cart_items = Cart.objects.filter(user=request.user)
    if not cart_items.exists():
        return redirect("cart")
        
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    if request.method == "POST":
        import json
        from django.http import JsonResponse
        
        try:
            data = json.loads(request.body)
            address_id = data.get("address_id")
            
            # 1. Resolve or create ShippingAddress
            if address_id:
                # Retrieve saved profile address
                addr = get_object_or_404(Address, id=address_id, user_profile__user=request.user)
                # Create a ShippingAddress record copy for this specific order
                shipping_address = ShippingAddress.objects.create(
                    user=request.user,
                    full_name=addr.full_name,
                    phone=addr.phone,
                    address_line_1=addr.address_line_1,
                    address_line_2=addr.address_line_2,
                    city=addr.city,
                    state=addr.state,
                    pincode=addr.pincode
                )
            else:
                full_name = data.get("full_name", "").strip()
                phone = data.get("phone", "").strip()
                address_line_1 = data.get("address_line_1", "").strip()
                address_line_2 = data.get("address_line_2", "").strip()
                city = data.get("city", "").strip()
                state = data.get("state", "").strip()
                pincode = data.get("pincode", "").strip()
                
                if not (full_name and phone and address_line_1 and city and state and pincode):
                    return JsonResponse({"error": "Please fill in all required shipping details."}, status=400)
                    
                shipping_address = ShippingAddress.objects.create(
                    user=request.user,
                    full_name=full_name,
                    phone=phone,
                    address_line_1=address_line_1,
                    address_line_2=address_line_2,
                    city=city,
                    state=state,
                    pincode=pincode
                )
                
                # Save to profile Address list for future orders
                profile, created = UserProfile.objects.get_or_create(user=request.user)
                Address.objects.create(
                    user_profile=profile,
                    full_name=full_name,
                    phone=phone,
                    address_line_1=address_line_1,
                    address_line_2=address_line_2,
                    city=city,
                    state=state,
                    pincode=pincode
                )
            
            # 2. Create the Order
            order = Order.objects.create(
                user=request.user,
                shipping_address=shipping_address,
                total_price=total,
                status="Pending"
            )
            
            # 3. Create OrderItems from Cart
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                )
                
            # 4. Clear the cart
            cart_items.delete()
            
            return JsonResponse({
                "status": "success",
                "message": "Order placed successfully!",
                "order_id": order.id
            })
            
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid request payload."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
            
    saved_addresses = Address.objects.filter(user_profile__user=request.user)
    
    return render(
        request,
        "shop/checkout.html",
        {
            "cart_items": cart_items,
            "total": total,
            "saved_addresses": saved_addresses
        }
    )
import random
from django.core.mail import send_mail
from django.conf import settings

def send_otp_test(request):

    otp = random.randint(100000, 999999)

    send_mail(
        "Velora Email Verification",
        f"Your OTP is {otp}",
        settings.EMAIL_HOST_USER,
        ["singh005rudra@gmail.com"],
        fail_silently=False,
    )

    return JsonResponse({
        "message": "OTP Sent",
        "otp": otp
    })

def verify_otp(request):

    if request.method == "POST":

        from django.contrib.auth.models import User
        from django.utils import timezone
        from datetime import timedelta

        entered_otp = request.POST.get("otp", "").strip()

        username = request.session.get("signup_username")
        email = request.session.get("signup_email")
        password = request.session.get("signup_password")

        if not (username and email and password):
            return render(
                request,
                "shop/verify_otp.html",
                {"error": "Session expired or invalid. Please sign up again."}
            )

        if User.objects.filter(username=username).exists():
            return render(
                request,
                "shop/verify_otp.html",
                {"error": "Username was taken while verifying. Please sign up again with a different username."}
            )

        if User.objects.filter(email__iexact=email).exists():
            return render(
                request,
                "shop/verify_otp.html",
                {"error": "Email was registered while verifying. Please log in or sign up with a different email."}
            )

        try:
            saved = EmailOTP.objects.get(email=email)

            if timezone.now() > saved.created_at + timedelta(minutes=10):
                saved.delete()
                return render(
                    request,
                    "shop/verify_otp.html",
                    {"error": "OTP has expired. Please sign up again to receive a new OTP."}
                )

            if saved.otp == entered_otp:
                # Valid OTP! Create user safely.
                User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )

                saved.delete()
                request.session.pop("signup_username", None)
                request.session.pop("signup_email", None)
                request.session.pop("signup_password", None)

                return redirect("login")
            else:
                return render(
                    request,
                    "shop/verify_otp.html",
                    {"error": "Invalid OTP. Please try again."}
                )

        except EmailOTP.DoesNotExist:
            return render(
                request,
                "shop/verify_otp.html",
                {"error": "No OTP found for this email. Please sign up again."}
            )

    return render(
        request,
        "shop/verify_otp.html"
    )

# =====================================
# WISHLIST FUNCTIONS
# =====================================

@login_required(login_url="/login/")
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required(login_url="/login/")
def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required(login_url="/login/")
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    wishlist_product_ids = [item.product.id for item in wishlist_items]
    return render(
        request,
        "shop/wishlist.html",
        {
            "wishlist_items": wishlist_items,
            "wishlist_product_ids": wishlist_product_ids
        }
    )

def logout_view(request):
    from django.contrib.auth import logout as django_logout
    django_logout(request)

    response = redirect("home")

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return response
def google_success(request):

    print("GOOGLE SUCCESS HIT")
    print("USER =", request.user)
    print("AUTH =", request.user.is_authenticated)

    if request.user.is_authenticated:

        access_token, refresh_token = generate_tokens(
            request.user
        )

        response = redirect("home")

        response.set_cookie(
            "access_token",
            access_token,
            httponly=True,
            samesite="Lax"
        )

        response.set_cookie(
            "refresh_token",
            refresh_token,
            httponly=True,
            samesite="Lax"
        )

        return response

    return redirect("login")

@jwt_login_required
def profile(request):

    profile, created = UserProfile.objects.get_or_create(
        user=request.user
    )

    addresses = Address.objects.filter(
        user_profile=profile
    )

    context = {
        "profile": profile,
        "addresses": addresses
    }

    return render(
        request,
        "shop/profile.html",
        context
    )

@jwt_login_required
def add_address(request):

    if request.method == "POST":
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        Address.objects.create(
            user_profile=profile,
            full_name=request.POST["full_name"],
            phone=request.POST["phone"],
            address_line_1=request.POST["address_line_1"],
            address_line_2=request.POST.get("address_line_2", ""),
            city=request.POST["city"],
            state=request.POST["state"],
            pincode=request.POST["pincode"]
        )

        return redirect("profile")

    return render(
        request,
        "shop/add_address.html"
    )

@jwt_login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user_profile__user=request.user)

    if request.method == "POST":
        address.full_name = request.POST["full_name"]
        address.phone = request.POST["phone"]
        address.address_line_1 = request.POST["address_line_1"]
        address.address_line_2 = request.POST.get("address_line_2", "")
        address.city = request.POST["city"]
        address.state = request.POST["state"]
        address.pincode = request.POST["pincode"]
        address.save()
        return redirect("profile")

    return render(
        request,
        "shop/edit_address.html",
        {
            "address": address
        }
    )

@jwt_login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user_profile__user=request.user)
    address.delete()
    return redirect("profile")

@jwt_login_required
def edit_profile(request):
    profile, created = UserProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":
        request.user.first_name = request.POST.get("first_name", "").strip()
        request.user.email = request.POST.get("email", "").strip()
        request.user.save()

        profile.phone = request.POST.get("phone", "").strip()
        
        dob_str = request.POST.get("date_of_birth", "").strip()
        if dob_str:
            profile.date_of_birth = dob_str
        else:
            profile.date_of_birth = None
            
        if "profile_image" in request.FILES:
            profile.profile_image = request.FILES["profile_image"]

        profile.save()

        return redirect("profile")

    return render(
        request,
        "shop/edit_profile.html",
        {
            "profile": profile
        }
    )

from django.shortcuts import redirect
from django.conf import settings


# =====================================
# FORGOT PASSWORD FLOW
# =====================================

def forgot_password(request):
    """Step 1: User enters email, OTP is sent."""
    if request.method == "POST":
        from django.contrib.auth.models import User
        import random
        from django.core.mail import send_mail as django_send_mail

        email = request.POST.get("email", "").strip()

        if not email:
            return render(
                request,
                "shop/forgot_password.html",
                {"error": "Please enter your email address."}
            )

        # Check if user with this email exists
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return render(
                request,
                "shop/forgot_password.html",
                {"error": "No account found with this email address."}
            )

        # Generate OTP
        otp = str(random.randint(100000, 999999))

        # Clean old OTPs for this email
        EmailOTP.objects.filter(email=email).delete()

        # Save new OTP
        EmailOTP.objects.create(email=email, otp=otp)

        # Store email in session
        request.session["reset_email"] = email

        # Send OTP email
        django_send_mail(
            "Velora Password Reset OTP",
            f"Your password reset OTP is: {otp}\n\nThis OTP is valid for 10 minutes. If you did not request a password reset, please ignore this email.",
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        return redirect("forgot_password_verify_otp")

    return render(request, "shop/forgot_password.html")


def forgot_password_verify_otp(request):
    """Step 2: User enters OTP to verify identity."""
    from django.utils import timezone
    from datetime import timedelta

    email = request.session.get("reset_email")
    if not email:
        return redirect("forgot_password")

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()

        try:
            saved = EmailOTP.objects.get(email=email)

            if timezone.now() > saved.created_at + timedelta(minutes=10):
                saved.delete()
                return render(
                    request,
                    "shop/forgot_password_verify_otp.html",
                    {"error": "OTP has expired. Please request a new one.", "email": email}
                )

            if saved.otp == entered_otp:
                # OTP verified! Allow password reset
                request.session["reset_verified"] = True
                saved.delete()
                return redirect("reset_password")
            else:
                return render(
                    request,
                    "shop/forgot_password_verify_otp.html",
                    {"error": "Invalid OTP. Please try again.", "email": email}
                )

        except EmailOTP.DoesNotExist:
            return render(
                request,
                "shop/forgot_password_verify_otp.html",
                {"error": "No OTP found. Please request a new one.", "email": email}
            )

    return render(
        request,
        "shop/forgot_password_verify_otp.html",
        {"email": email}
    )


def reset_password(request):
    """Step 3: User sets a new password after OTP verification."""
    email = request.session.get("reset_email")
    verified = request.session.get("reset_verified")

    if not email or not verified:
        return redirect("forgot_password")

    if request.method == "POST":
        from django.contrib.auth.models import User

        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if not password1 or not password2:
            return render(
                request,
                "shop/reset_password.html",
                {"error": "Please fill in both password fields."}
            )

        if password1 != password2:
            return render(
                request,
                "shop/reset_password.html",
                {"error": "Passwords do not match."}
            )

        if len(password1) < 8:
            return render(
                request,
                "shop/reset_password.html",
                {"error": "Password must be at least 8 characters long."}
            )

        try:
            user = User.objects.get(email__iexact=email)
            user.set_password(password1)
            user.save()

            # Clean up session
            request.session.pop("reset_email", None)
            request.session.pop("reset_verified", None)

            from django.contrib import messages
            messages.success(request, "Password reset successful! Please login with your new password.")
            return redirect("login")

        except User.DoesNotExist:
            return render(
                request,
                "shop/reset_password.html",
                {"error": "User account not found. Please try again."}
            )

    return render(request, "shop/reset_password.html")

def google_login(request):
    google_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        f"&client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        "&scope=openid%20email%20profile"
    )

    return redirect(google_url)