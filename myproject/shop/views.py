import json
import random
import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Avg, Q
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth import authenticate, login as auth_login, logout as django_logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.contrib import messages
from django.contrib.postgres.search import TrigramSimilarity
from django.contrib.auth.decorators import login_required

from datetime import timedelta

from .models import Product, Category, Review, Cart, EmailOTP, Wishlist, UserProfile, Address, UserInteraction, Order
from .decorators import jwt_login_required
from .auth_helpers import generate_tokens

logger = logging.getLogger(__name__)


# =====================================
# HELPER FUNCTIONS (not views)
# =====================================

def get_fuzzy_search_results(query_str, queryset, limit=None):
    query_str = query_str.strip()
    if not query_str:
        return list(queryset)

    # 1. Detect if the query is a natural language detailed query
    words = query_str.split()
    nl_keywords = {
        'under', 'above', 'between', 'for', 'in', 'with', 'cheap', 'best',
        'chahiye', 'wala', 'wale', 'me', 'ke', 'liye', 'sasta', 'achha', 'good', 'bad', 'gaming', 'office', 'student'
    }
    is_natural_language = len(words) > 2 or any(w.lower().strip('?.!,') in nl_keywords for w in words)

    matched_products = []
    is_semantic = False

    # 2. Exact/Contains Match FIRST (Crucial for short queries like "s" or "shoes")
    if not is_natural_language:
        direct_matches = queryset.filter(
            Q(name__icontains=query_str) | 
            Q(category_fk__name__icontains=query_str) | 
            Q(category__icontains=query_str)
        ).distinct()
        
        if direct_matches.exists():
            matched_products = list(direct_matches)

    # If the query is just 1 or 2 letters (e.g. "s"), STOP here. Trigram and Semantic search will return garbage.
    if len(query_str) < 3:
        if limit:
            return matched_products[:limit]
        return matched_products

    # 3. If exact match didn't find enough, try fuzzy matching (Trigram)
    if not is_natural_language and len(matched_products) < 3:
        try:
            fuzzy_qs = queryset.annotate(
                similarity=TrigramSimilarity('name', query_str) + TrigramSimilarity('category', query_str)
            ).filter(similarity__gt=0.3).order_by('-similarity', '-id')
            
            existing_ids = {p.id for p in matched_products}
            for p in fuzzy_qs:
                if p.id not in existing_ids:
                    matched_products.append(p)
        except Exception as e:
            logger.error(f"Fuzzy search failed: {e}")

    # 4. If fuzzy search still returned NO results, or it's a natural language query, run semantic search
    if len(matched_products) == 0 or is_natural_language:
        try:
            from chatbot.services.vector_search import search_products
            top_k = limit if limit else 30
            semantic_results, _ = search_products(query_str, top_k=top_k)

            if semantic_results:
                product_ids = [p['id'] for p in semantic_results]

                # Fetch Django Product objects preserving the similarity order
                from django.db.models import Case, When
                preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(product_ids)])

                semantic_qs = queryset.filter(id__in=product_ids).order_by(preserved_order)
                
                # Append semantic results without overwriting exact/fuzzy matches!
                existing_ids = {p.id for p in matched_products}
                for p in semantic_qs:
                    if p.id not in existing_ids:
                        matched_products.append(p)
                        
                is_semantic = True
                logger.info(f"Triggered semantic search for query: '{query_str}', found total {len(matched_products)} products.")
        except Exception as sem_err:
            logger.error(f"Semantic search failed fallback: {sem_err}", exc_info=True)

            # Fallback to fuzzy search if not already run
            if is_natural_language:
                try:
                    fuzzy_qs = queryset.annotate(
                        similarity=TrigramSimilarity('name', query_str) + TrigramSimilarity('category', query_str)
                    ).filter(similarity__gt=0.1).order_by('-similarity', '-id')
                    matched_products = list(fuzzy_qs)
                except Exception as e:
                    logger.error(f"Fuzzy fallback failed: {e}")

    if limit:
        matched_products = matched_products[:limit]

    # Tag the list to indicate if semantic search was used
    try:
        matched_products.is_semantic = is_semantic
    except AttributeError:
        pass

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


def _apply_sorting(queryset, sort_by):
    """Apply sorting to a Django QuerySet (used when search is not active)."""
    if sort_by == "price_low":
        return queryset.order_by("price")
    elif sort_by == "price_high":
        return queryset.order_by("-price")
    elif sort_by == "alphabet":
        return queryset.order_by("name")
    elif sort_by == "alphabet_desc":
        return queryset.order_by("-name")
    elif sort_by in ["rating", "popular"]:
        return queryset.annotate(avg_rating=Avg("reviews__rating")).order_by("-avg_rating")
    else:
        return queryset.order_by("-id")


def _serialize_products(products):
    """Serialize product page objects for AJAX responses."""
    product_data = []
    for product in products:
        product_data.append({
            "id": product.id,
            "name": product.name,
            "price": str(product.price),
            "description": product.description,
            "image": product.image,
            "rating": product.average_rating,
            "reviews": product.total_reviews,
        })
    return product_data


def _get_wishlist_ids(user):
    """Return list of wishlisted product IDs for an authenticated user."""
    if user.is_authenticated:
        return list(Wishlist.objects.filter(user=user).values_list('product_id', flat=True))
    return []

def track_interaction(user, product, interaction_type):
    """Stores a UserInteraction record if the user is authenticated."""
    if user.is_authenticated:
        UserInteraction.objects.create(
            user=user, 
            product=product, 
            interaction_type=interaction_type
        )


# =====================================
# HOME
# =====================================

class HomeView(View):
    def get(self, request):
        search = request.GET.get("search", "").strip()
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
        semantic_search_used = False
        if search:
            matched_list = get_fuzzy_search_results(search, products_queryset)
            semantic_search_used = getattr(matched_list, 'is_semantic', False)
            products_queryset = sort_products_list(matched_list, sort_by)
        else:
            products_queryset = _apply_sorting(products_queryset, sort_by)

        # PAGINATION
        paginator = Paginator(products_queryset, 12)
        products = paginator.get_page(page_number)

        # AJAX REQUEST
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "products": _serialize_products(products),
                "has_next": products.has_next(),
                "current_page": products.number,
            })

        categories = Category.objects.all()

        context = {
            "products": products,
            "featured_products": featured_products,
            "categories": categories,
            "search": search,
            "semantic_search_used": semantic_search_used,
            "selected_category": category_id,
            "category": category_id,
            "collection_name": collection_name,
            "collection_title": collection_title,
            "sort_by": sort_by,
            "wishlist_product_ids": _get_wishlist_ids(request.user),
        }

        return render(request, "shop/home.html", context)


# =====================================
# PRODUCTS LIST
# =====================================

class ProductListView(View):
    def get(self, request):
        search = request.GET.get("search", "").strip()
        category_id = request.GET.get("category", "").strip()
        collection_name = request.GET.get("collection", "").strip()
        sort_by = request.GET.get("sort", "")
        page_number = request.GET.get("page", 1)

        products_queryset = Product.objects.all()
        title = "All Products"

        # Collection Filter
        if collection_name:
            if collection_name == "new-arrivals":
                products_queryset = products_queryset.order_by('-id')
                title = "New Arrivals"
            elif collection_name == "best-sellers":
                from django.db.models import Count, Avg
                products_queryset = products_queryset.annotate(
                    review_count=Count('reviews'),
                    avg_rating=Avg('reviews__rating')
                ).filter(review_count__gt=0).order_by('-avg_rating', '-review_count')
                title = "Best Sellers"
            elif collection_name == "collectors-editions":
                products_queryset = products_queryset.filter(price__gte=10000).order_by('-price')
                title = "Collector's Editions"
            else:
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
        semantic_search_used = False
        if search:
            matched_list = get_fuzzy_search_results(search, products_queryset)
            semantic_search_used = getattr(matched_list, 'is_semantic', False)
            products_queryset = sort_products_list(matched_list, sort_by)
        else:
            products_queryset = _apply_sorting(products_queryset, sort_by)

        # Pagination
        paginator = Paginator(products_queryset, 12)
        products = paginator.get_page(page_number)

        # AJAX Request
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "products": _serialize_products(products),
                "has_next": products.has_next(),
                "current_page": products.number,
            })

        categories = Category.objects.all()

        context = {
            "products": products,
            "categories": categories,
            "search": search,
            "semantic_search_used": semantic_search_used,
            "title": title,
            "selected_category": category_id,
            "category_id": category_id,
            "collection_name": collection_name,
            "sort_by": sort_by,
            "wishlist_product_ids": _get_wishlist_ids(request.user),
        }

        return render(request, "shop/product_list.html", context)


# =====================================
# PRODUCT DETAIL + REVIEWS
# =====================================

class ProductDetailView(View):
    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        
        track_interaction(request.user, product, 'view')

        reviews_list = product.reviews.all().order_by("-id")
        paginator = Paginator(reviews_list, 5)
        page_number = request.GET.get("page")
        reviews = paginator.get_page(page_number)

        return render(request, "shop/product_detail.html", {
            "product": product,
            "reviews": reviews,
            "wishlist_product_ids": _get_wishlist_ids(request.user),
        })

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)

        Review.objects.create(
            product=product,
            customer_name=request.POST.get("customer_name"),
            email=request.POST.get("email"),
            rating=request.POST.get("rating"),
            title=request.POST.get("title", ""),
            review_text=request.POST.get("review_text"),
        )
        
        track_interaction(request.user, product, 'review')

        return redirect("product_detail", product_id=product.id)


# =====================================
# SEARCH SUGGESTIONS
# =====================================

class SearchSuggestionsView(View):
    def get(self, request):
        term = request.GET.get("term", "").strip()

        if not term:
            return JsonResponse([], safe=False)

        all_products = Product.objects.all()
        matched_products = get_fuzzy_search_results(term, all_products, limit=10)

        data = []
        for product in matched_products:
            data.append({
                "id": product.id,
                "name": product.name,
                "price": str(product.price),
            })

        return JsonResponse(data, safe=False)


# =====================================
# CART FUNCTIONS
# =====================================

@method_decorator(jwt_login_required, name="dispatch")
class AddToCartView(View):
    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)

        # Block out-of-stock products
        if product.stock <= 0:
            messages.error(request, f"{product.name} is currently out of stock!")
            return redirect("product_detail", product_id=product.id)

        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            product=product,
        )
        if not created:
            cart_item.quantity += 1
            cart_item.save()
            
        track_interaction(request.user, product, 'cart')
        
        return redirect("cart")


@method_decorator(jwt_login_required, name="dispatch")
class CartView(View):
    def get(self, request):
        cart_items = Cart.objects.filter(user=request.user)
        total = sum(item.product.price * item.quantity for item in cart_items)
        return render(request, "shop/cart.html", {
            "cart_items": cart_items,
            "total": total,
        })


@method_decorator(login_required(login_url="/login/"), name="dispatch")
class IncreaseQuantityView(View):
    def get(self, request, product_id):
        item = get_object_or_404(Cart, user=request.user, product_id=product_id)
        item.quantity += 1
        item.save()
        return redirect("cart")


@method_decorator(login_required(login_url="/login/"), name="dispatch")
class DecreaseQuantityView(View):
    def get(self, request, product_id):
        item = get_object_or_404(Cart, user=request.user, product_id=product_id)
        item.quantity -= 1
        if item.quantity <= 0:
            item.delete()
        else:
            item.save()
        return redirect("cart")


@method_decorator(login_required(login_url="/login/"), name="dispatch")
class RemoveFromCartView(View):
    def get(self, request, product_id):
        Cart.objects.filter(user=request.user, product_id=product_id).delete()
        return redirect("cart")


@method_decorator(login_required(login_url="/login/"), name="dispatch")
class ClearCartView(View):
    def get(self, request):
        Cart.objects.filter(user=request.user).delete()
        return redirect("cart")


# =====================================
# AUTH: LOGIN
# =====================================

class LoginView(View):
    def get(self, request):
        return render(request, "shop/login.html", {
            "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID,
        })

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            access_token, refresh_token = generate_tokens(user)

            redirect_url = "/"
            if hasattr(user, "userprofile"):
                if user.userprofile.role == "admin":
                    redirect_url = "/admin/dashboard/"
                elif user.userprofile.role == "support":
                    redirect_url = "/admin/chat/"

            response = redirect(redirect_url)
            response.set_cookie("access_token", access_token, httponly=True, samesite="Lax")
            response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="Lax")
            return response

        return render(request, "shop/login.html", {
            "error": "Invalid Credentials",
            "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID,
        })


class LoginPageView(View):
    """Alternate login using Django session auth (kept for backward compatibility)."""

    def get(self, request):
        return render(request, "shop/login.html")

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            
            redirect_url = "/"
            if hasattr(user, "userprofile"):
                if user.userprofile.role == "admin":
                    redirect_url = "/admin/dashboard/"
                elif user.userprofile.role == "support":
                    redirect_url = "/admin/chat/"
                    
            return redirect(redirect_url)

        return render(request, "shop/login.html", {"error": "Invalid Credentials"})


# =====================================
# AUTH: SIGNUP
# =====================================

class SignupView(View):
    def get(self, request):
        return render(request, "shop/signup.html", {
            "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID,
        })

    def post(self, request):
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        ctx = {"GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID}

        if password1 != password2:
            ctx["error"] = "Passwords do not match"
            return render(request, "shop/signup.html", ctx)

        if User.objects.filter(username=username).exists():
            ctx["error"] = "Username already exists. Choose another username."
            return render(request, "shop/signup.html", ctx)

        if User.objects.filter(email__iexact=email).exists():
            ctx["error"] = "An account with this email already exists."
            return render(request, "shop/signup.html", ctx)

        otp = str(random.randint(100000, 999999))

        EmailOTP.objects.filter(email=email).delete()
        EmailOTP.objects.create(email=email, otp=otp)

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


# =====================================
# CHECKOUT
# =====================================

@method_decorator(jwt_login_required, name="dispatch")
class CheckoutView(View):
    def get(self, request):
        from .models import ShippingAddress, Order, OrderItem

        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items.exists():
            return redirect("cart")

        total = sum(item.product.price * item.quantity for item in cart_items)
        saved_addresses = Address.objects.filter(user_profile__user=request.user)
        default_address = saved_addresses.filter(is_default=True).first()
        if not default_address:
            default_address = saved_addresses.first()

        return render(request, "shop/checkout.html", {
            "cart_items": cart_items,
            "total": total,
            "saved_addresses": saved_addresses,
            "default_address": default_address,
        })

    def post(self, request):
        from .models import ShippingAddress, Order, OrderItem

        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items.exists():
            return redirect("cart")

        total = sum(item.product.price * item.quantity for item in cart_items)

        try:
            data = json.loads(request.body)
            address_id = data.get("address_id")

            # 1. Resolve or create ShippingAddress
            if address_id:
                addr = get_object_or_404(Address, id=address_id, user_profile__user=request.user)
                shipping_address = ShippingAddress.objects.create(
                    user=request.user,
                    full_name=addr.full_name,
                    phone=addr.phone,
                    address_line_1=addr.address_line_1,
                    address_line_2=addr.address_line_2,
                    city=addr.city,
                    state=addr.state,
                    pincode=addr.pincode,
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
                    pincode=pincode,
                )

                # Save to profile Address list for future orders
                profile, _ = UserProfile.objects.get_or_create(user=request.user)
                Address.objects.create(
                    user_profile=profile,
                    full_name=full_name,
                    phone=phone,
                    address_line_1=address_line_1,
                    address_line_2=address_line_2,
                    city=city,
                    state=state,
                    pincode=pincode,
                )

            payment_method = data.get("payment_method", "Online")

            if payment_method == "COD":
                # Validate COD Eligibility
                from .services.payment_service import PaymentService
                is_eligible, reason = PaymentService.validate_cod_eligibility(cart_items, shipping_address)
                if not is_eligible:
                    # Rolling back address creation (optional)
                    shipping_address.delete()
                    return JsonResponse({"error": reason}, status=400)
                
                # Create Order for COD
                order = Order.objects.create(
                    user=request.user,
                    shipping_address=shipping_address,
                    total_price=total,
                    status="Pending",
                    payment_method="COD",
                    payment_status="Pending"
                )

                # Create OrderItems
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order, product=item.product, quantity=item.quantity, price=item.product.price
                    )
                    track_interaction(request.user, item.product, 'purchase')

                cart_items.delete()

                # Generate Invoice for COD
                from .services.invoice_service import InvoiceService
                InvoiceService.generate_invoice(order)

                return JsonResponse({
                    "status": "success",
                    "message": "Order placed successfully using Cash on Delivery.",
                    "order_id": order.id,
                    "payment_method": "COD"
                })
            else:
                # Generate Razorpay Order
                import razorpay
                from django.conf import settings
                
                client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                amount_in_paise = int(total * 100)
                
                razorpay_order = client.order.create({
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "payment_capture": "1"
                })

                # Create Order for Online Payment
                order = Order.objects.create(
                    user=request.user,
                    shipping_address=shipping_address,
                    total_price=total,
                    status="Pending",
                    payment_method="Online",
                    payment_status="Pending",
                    razorpay_order_id=razorpay_order['id']
                )

                # Create OrderItems
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order, product=item.product, quantity=item.quantity, price=item.product.price
                    )
                    track_interaction(request.user, item.product, 'purchase')

                cart_items.delete()

                return JsonResponse({
                    "status": "success",
                    "message": "Order created, proceed to payment.",
                    "order_id": order.id,
                    "razorpay_order_id": razorpay_order['id'],
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "key_id": settings.RAZORPAY_KEY_ID,
                    "payment_method": "Online"
                })

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid request payload."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# =====================================
# VERIFY PAYMENT
# =====================================

@method_decorator(jwt_login_required, name="dispatch")
class ValidateCODView(View):
    def post(self, request):
        from .models import Address, Cart
        from .services.payment_service import PaymentService
        
        try:
            data = json.loads(request.body)
            address_id = data.get("address_id")
            
            if not address_id:
                return JsonResponse({"eligible": False, "reason": "No address provided"})
                
            address = get_object_or_404(Address, id=address_id, user_profile__user=request.user)
            cart_items = Cart.objects.filter(user=request.user)
            
            is_eligible, reason = PaymentService.validate_cod_eligibility(cart_items, address)
            
            return JsonResponse({
                "eligible": is_eligible,
                "reason": reason
            })
        except Exception as e:
            return JsonResponse({"eligible": False, "reason": str(e)}, status=500)


@method_decorator(jwt_login_required, name="dispatch")
class VerifyPaymentView(View):
    def post(self, request):
        from .models import Order
        import razorpay
        from django.conf import settings
        
        try:
            data = json.loads(request.body)
            razorpay_payment_id = data.get("razorpay_payment_id")
            razorpay_order_id = data.get("razorpay_order_id")
            razorpay_signature = data.get("razorpay_signature")
            order_id = data.get("order_id")

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            # Verify the signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            client.utility.verify_payment_signature(params_dict)

            # Mark order as confirmed
            order = get_object_or_404(Order, id=order_id, user=request.user)
            order.status = "Confirmed"
            order.payment_status = "Paid"
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature
            order.save()

            # Automatically generate invoice
            from .services.invoice_service import InvoiceService
            InvoiceService.generate_invoice(order)

            return JsonResponse({"status": "success", "message": "Payment verified successfully!"})

        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({"error": "Payment signature verification failed."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# =====================================
# ORDER CONFIRMATION
# =====================================

@method_decorator(jwt_login_required, name="dispatch")
class OrderConfirmationView(View):
    def get(self, request, order_id):
        from .models import Order, OrderItem

        order = get_object_or_404(
            Order,
            id=order_id,
            user=request.user
        )
        order_items = OrderItem.objects.filter(
            order=order
        ).select_related("product")

        return render(request, "shop/order_confirmation.html", {
            "order": order,
            "order_items": order_items,
        })


# =====================================
# ORDERS HISTORY
# =====================================

@method_decorator(jwt_login_required, name="dispatch")
class OrdersView(View):
    def get(self, request):
        from .models import Order
        # Fetch orders for the logged-in user, ordered by newest first
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        return render(request, "shop/orders.html", {"orders": orders})


# =====================================
# STOCK NOTIFICATION
# =====================================

class NotifyStockView(View):
    def post(self, request, product_id):
        from .models import StockNotification

        product = get_object_or_404(Product, id=product_id)

        if product.stock > 0:
            return JsonResponse(
                {"status": "error", "message": "Product is already in stock!"},
                status=400
            )

        email = None
        try:
            data = json.loads(request.body)
            email = data.get("email", "").strip()
        except (json.JSONDecodeError, AttributeError):
            email = request.POST.get("email", "").strip()

        if not email:
            if request.user.is_authenticated and request.user.email:
                email = request.user.email
            else:
                return JsonResponse(
                    {"status": "error", "message": "Please provide a valid email."},
                    status=400
                )

        # Create or get notification subscription
        _, created = StockNotification.objects.get_or_create(
            email=email,
            product=product,
            defaults={"notified": False}
        )

        if created:
            return JsonResponse({
                "status": "success",
                "message": f"We'll notify {email} when {product.name} is back in stock!"
            })
        else:
            return JsonResponse({
                "status": "info",
                "message": f"{email} is already subscribed for this product."
            })


# =====================================
# OTP
# =====================================

class SendOTPTestView(View):
    def get(self, request):
        otp = random.randint(100000, 999999)

        send_mail(
            "Velora Email Verification",
            f"Your OTP is {otp}",
            settings.EMAIL_HOST_USER,
            ["singh005rudra@gmail.com"],
            fail_silently=False,
        )

        return JsonResponse({"message": "OTP Sent", "otp": otp})


class VerifyOTPView(View):
    def get(self, request):
        return render(request, "shop/verify_otp.html")

    def post(self, request):
        entered_otp = request.POST.get("otp", "").strip()

        username = request.session.get("signup_username")
        email = request.session.get("signup_email")
        password = request.session.get("signup_password")

        if not (username and email and password):
            return render(request, "shop/verify_otp.html", {
                "error": "Session expired or invalid. Please sign up again.",
            })

        if User.objects.filter(username=username).exists():
            return render(request, "shop/verify_otp.html", {
                "error": "Username was taken while verifying. Please sign up again with a different username.",
            })

        if User.objects.filter(email__iexact=email).exists():
            return render(request, "shop/verify_otp.html", {
                "error": "Email was registered while verifying. Please log in or sign up with a different email.",
            })

        try:
            saved = EmailOTP.objects.get(email=email)

            if timezone.now() > saved.created_at + timedelta(minutes=10):
                saved.delete()
                return render(request, "shop/verify_otp.html", {
                    "error": "OTP has expired. Please sign up again to receive a new OTP.",
                })

            if saved.otp == entered_otp:
                # Valid OTP! Create user safely.
                User.objects.create_user(username=username, email=email, password=password)

                saved.delete()
                request.session.pop("signup_username", None)
                request.session.pop("signup_email", None)
                request.session.pop("signup_password", None)

                return redirect("login")
            else:
                return render(request, "shop/verify_otp.html", {
                    "error": "Invalid OTP. Please try again.",
                })

        except EmailOTP.DoesNotExist:
            return render(request, "shop/verify_otp.html", {
                "error": "No OTP found for this email. Please sign up again.",
            })


# =====================================
# WISHLIST FUNCTIONS
# =====================================

@method_decorator(login_required(login_url="/login/"), name="dispatch")
class AddToWishlistView(View):
    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        Wishlist.objects.get_or_create(user=request.user, product=product)
        track_interaction(request.user, product, 'wishlist')
        return redirect(request.META.get('HTTP_REFERER', 'home'))


@method_decorator(login_required(login_url="/login/"), name="dispatch")
class RemoveFromWishlistView(View):
    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        Wishlist.objects.filter(user=request.user, product=product).delete()
        return redirect(request.META.get('HTTP_REFERER', 'home'))


@method_decorator(login_required(login_url="/login/"), name="dispatch")
class WishlistView(View):
    def get(self, request):
        wishlist_items = Wishlist.objects.filter(user=request.user)
        wishlist_product_ids = [item.product.id for item in wishlist_items]
        return render(request, "shop/wishlist.html", {
            "wishlist_items": wishlist_items,
            "wishlist_product_ids": wishlist_product_ids,
        })


# =====================================
# LOGOUT
# =====================================

class LogoutView(View):
    def get(self, request):
        return self.post(request)

    def post(self, request):
        django_logout(request)

        response = redirect("home")
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response


# =====================================
# GOOGLE AUTH
# =====================================

class GoogleSuccessView(View):
    def get(self, request):
        print("GOOGLE SUCCESS HIT")
        print("USER =", request.user)
        print("AUTH =", request.user.is_authenticated)

        if request.user.is_authenticated:
            access_token, refresh_token = generate_tokens(request.user)

            redirect_url = "/"
            if hasattr(request.user, "userprofile"):
                if request.user.userprofile.role == "admin":
                    redirect_url = "/admin/dashboard/"
                elif request.user.userprofile.role == "support":
                    redirect_url = "/admin/chat/"

            response = redirect(redirect_url)
            response.set_cookie("access_token", access_token, httponly=True, samesite="Lax")
            response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="Lax")
            return response

        return redirect("login")


class GoogleLoginView(View):
    def get(self, request):
        google_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            "?response_type=code"
            f"&client_id={settings.GOOGLE_CLIENT_ID}"
            f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
            "&scope=openid%20email%20profile"
        )
        return redirect(google_url)


# =====================================
# PROFILE
# =====================================

@method_decorator(jwt_login_required, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class ProfileView(View):
    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        # Only pass the default address
        default_address = Address.objects.filter(user_profile=profile, is_default=True).first()

        return render(request, "shop/profile.html", {
            "profile": profile,
            "default_address": default_address,
        })


@method_decorator(jwt_login_required, name="dispatch")
class AddressesView(View):
    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        addresses = Address.objects.filter(user_profile=profile)

        return render(request, "shop/addresses.html", {
            "addresses": addresses,
        })


@method_decorator(jwt_login_required, name="dispatch")
class EditProfileView(View):
    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return render(request, "shop/edit_profile.html", {"profile": profile})

    def post(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        request.user.first_name = request.POST.get("first_name", "").strip()
        request.user.email = request.POST.get("email", "").strip()
        request.user.save()

        profile.phone = request.POST.get("phone", "").strip()

        dob_str = request.POST.get("date_of_birth", "").strip()
        if dob_str:
            profile.date_of_birth = dob_str
        else:
            profile.date_of_birth = None

        if request.POST.get("remove_image"):
            if profile.profile_image:
                profile.profile_image.delete(save=False)
                profile.profile_image = None
        elif "profile_image" in request.FILES:
            profile.profile_image = request.FILES["profile_image"]

        # Save avatar selection
        avatar = request.POST.get("avatar", "").strip()
        if avatar:
            profile.avatar = avatar

        profile.save()

        return redirect("profile")


# =====================================
# ADDRESS MANAGEMENT
# =====================================

@method_decorator(jwt_login_required, name="dispatch")
class SetDefaultAddressView(View):
    def get(self, request, address_id):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        try:
            # First set all addresses for this profile to not default
            Address.objects.filter(user_profile=profile).update(is_default=False)
            # Then set the selected one as default
            address = Address.objects.get(id=address_id, user_profile=profile)
            address.is_default = True
            address.save()
        except Address.DoesNotExist:
            pass
        return redirect("addresses")

@method_decorator(jwt_login_required, name="dispatch")
class AddAddressView(View):
    def get(self, request):
        return render(request, "shop/add_address.html")

    def post(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        Address.objects.create(
            user_profile=profile,
            full_name=request.POST["full_name"],
            phone=request.POST["phone"],
            address_line_1=request.POST["address_line_1"],
            address_line_2=request.POST.get("address_line_2", ""),
            city=request.POST["city"],
            state=request.POST["state"],
            pincode=request.POST["pincode"],
        )
        return redirect("addresses")


@method_decorator(jwt_login_required, name="dispatch")
class EditAddressView(View):
    def get(self, request, address_id):
        address = get_object_or_404(Address, id=address_id, user_profile__user=request.user)
        return render(request, "shop/edit_address.html", {"address": address})

    def post(self, request, address_id):
        address = get_object_or_404(Address, id=address_id, user_profile__user=request.user)
        address.full_name = request.POST["full_name"]
        address.phone = request.POST["phone"]
        address.address_line_1 = request.POST["address_line_1"]
        address.address_line_2 = request.POST.get("address_line_2", "")
        address.city = request.POST["city"]
        address.state = request.POST["state"]
        address.pincode = request.POST["pincode"]
        address.save()
        return redirect("addresses")


@method_decorator(jwt_login_required, name="dispatch")
class DeleteAddressView(View):
    def get(self, request, address_id):
        address = get_object_or_404(Address, id=address_id, user_profile__user=request.user)
        address.delete()
        return redirect("addresses")


# =====================================
# FORGOT PASSWORD FLOW
# =====================================

class ForgotPasswordView(View):
    """Step 1: User enters email, OTP is sent."""

    def get(self, request):
        return render(request, "shop/forgot_password.html")

    def post(self, request):
        email = request.POST.get("email", "").strip()

        if not email:
            return render(request, "shop/forgot_password.html", {
                "error": "Please enter your email address.",
            })

        # Check if user with this email exists
        try:
            User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return render(request, "shop/forgot_password.html", {
                "error": "No account found with this email address.",
            })

        # Generate OTP
        otp = str(random.randint(100000, 999999))

        # Clean old OTPs for this email
        EmailOTP.objects.filter(email=email).delete()

        # Save new OTP
        EmailOTP.objects.create(email=email, otp=otp)

        # Store email in session
        request.session["reset_email"] = email

        # Send OTP email
        send_mail(
            "Velora Password Reset OTP",
            f"Your password reset OTP is: {otp}\n\nThis OTP is valid for 10 minutes. If you did not request a password reset, please ignore this email.",
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        return redirect("forgot_password_verify_otp")


class ForgotPasswordVerifyOTPView(View):
    """Step 2: User enters OTP to verify identity."""

    def get(self, request):
        email = request.session.get("reset_email")
        if not email:
            return redirect("forgot_password")
        return render(request, "shop/forgot_password_verify_otp.html", {"email": email})

    def post(self, request):
        email = request.session.get("reset_email")
        if not email:
            return redirect("forgot_password")

        entered_otp = request.POST.get("otp", "").strip()

        try:
            saved = EmailOTP.objects.get(email=email)

            if timezone.now() > saved.created_at + timedelta(minutes=10):
                saved.delete()
                return render(request, "shop/forgot_password_verify_otp.html", {
                    "error": "OTP has expired. Please request a new one.",
                    "email": email,
                })

            if saved.otp == entered_otp:
                # OTP verified! Allow password reset
                request.session["reset_verified"] = True
                saved.delete()
                return redirect("reset_password")
            else:
                return render(request, "shop/forgot_password_verify_otp.html", {
                    "error": "Invalid OTP. Please try again.",
                    "email": email,
                })

        except EmailOTP.DoesNotExist:
            return render(request, "shop/forgot_password_verify_otp.html", {
                "error": "No OTP found. Please request a new one.",
                "email": email,
            })


class ResetPasswordView(View):
    """Step 3: User sets a new password after OTP verification."""

    def get(self, request):
        email = request.session.get("reset_email")
        verified = request.session.get("reset_verified")

        if not email or not verified:
            return redirect("forgot_password")

        return render(request, "shop/reset_password.html")

    def post(self, request):
        email = request.session.get("reset_email")
        verified = request.session.get("reset_verified")

        if not email or not verified:
            return redirect("forgot_password")

        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if not password1 or not password2:
            return render(request, "shop/reset_password.html", {
                "error": "Please fill in both password fields.",
            })

        if password1 != password2:
            return render(request, "shop/reset_password.html", {
                "error": "Passwords do not match.",
            })

        if len(password1) < 8:
            return render(request, "shop/reset_password.html", {
                "error": "Password must be at least 8 characters long.",
            })

        try:
            user = User.objects.get(email__iexact=email)
            user.set_password(password1)
            user.save()

            # Clean up session
            request.session.pop("reset_email", None)
            request.session.pop("reset_verified", None)

            messages.success(request, "Password reset successful! Please login with your new password.")
            return redirect("login")

        except User.DoesNotExist:
            return render(request, "shop/reset_password.html", {
                "error": "User account not found. Please try again.",
            })

# =====================================
# RECOMMENDATIONS API
# =====================================

from shop.services.recommendation_service import RecommendationEngine

class RecommendationAPIView(View):
    """
    GET /api/recommendations/
    Returns personalized top 10 product recommendations.
    """
    def get(self, request):
        context_type = request.GET.get('type', 'general')
        product_id = request.GET.get('product_id')
        cart_ids = request.GET.get('cart_ids')
        
        if product_id and product_id.isdigit():
            product_id = int(product_id)
        else:
            product_id = None
            
        recommendations = RecommendationEngine.get_recommendations(
            user=request.user, 
            limit=10,
            context_type=context_type,
            target_id=product_id,
            cart_ids=cart_ids
        )
        
        data = {
            "recommendations": [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": str(p.price),
                    "image": p.image,
                    "category": p.category_fk.name if p.category_fk else p.category,
                    "rating": p.average_rating,
                }
                for p in recommendations
            ]
        }
        
        return JsonResponse(data)


from .models import RefundRequest

class RequestRefundView(View):
    def post(self, request, order_id):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
            
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            
            # Check if eligible
            if order.status not in ["Confirmed", "Delivered"]:
                messages.error(request, "This order is not eligible for a refund.")
                return redirect('orders')
                
            # Check if refund already requested
            if hasattr(order, 'refund_request'):
                messages.warning(request, "Refund already requested for this order.")
                return redirect('orders')
                
            reason = request.POST.get('reason', '').strip()
            if not reason:
                messages.error(request, "Please provide a reason for the refund.")
                return redirect('orders')
                
            # Create refund request
            RefundRequest.objects.create(
                order=order,
                user=request.user,
                reason=reason
            )
            
            messages.success(request, f"Refund requested successfully for Order #{order.id}.")
            return redirect('orders')
            
        except Order.DoesNotExist:
            messages.error(request, "Order not found.")
            return redirect('orders')