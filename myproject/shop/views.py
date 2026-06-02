from django.shortcuts import (
    render,
    get_object_or_404,
    redirect
)

from django.http import JsonResponse

from django.core.paginator import Paginator

from django.db.models import Q

from rapidfuzz import fuzz

from .models import (
    Product,
    Review
)


# =====================================
# HOME
# =====================================

def home(request):

    search = request.GET.get("search", "").strip()
    page_number = request.GET.get("page", 1)

    featured_products = Product.objects.order_by("?")[:20]

    products_queryset = Product.objects.all().order_by("-id")

    if search:

        exact_products = Product.objects.filter(
            Q(name__icontains=search) |
            Q(category__icontains=search) |
            Q(description__icontains=search)
        )

        exact_ids = list(
            exact_products.values_list(
                "id",
                flat=True
            )
        )

        fuzzy_scores = {}

        for product in products_queryset:

            score_name = fuzz.partial_ratio(
                search.lower(),
                product.name.lower()
            )

            score_category = fuzz.partial_ratio(
                search.lower(),
                product.category.lower()
            )

            score_description = fuzz.partial_ratio(
                search.lower(),
                product.description.lower()
            )

            best_score = max(
                score_name,
                score_category,
                score_description
            )

            if best_score >= 65:
                fuzzy_scores[product.id] = best_score

        fuzzy_ids = sorted(
            fuzzy_scores,
            key=fuzzy_scores.get,
            reverse=True
        )

        final_ids = []

        for pid in exact_ids + fuzzy_ids:
            if pid not in final_ids:
                final_ids.append(pid)

        products_queryset = Product.objects.filter(
            id__in=final_ids
        )

    paginator = Paginator(products_queryset, 10)
    products = paginator.get_page(page_number)

    # AJAX Infinite Scroll
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

    return render(
        request,
        "shop/home.html",
        {
            "products": products,
            "search": search,
            "featured_products": featured_products
        }
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

    reviews = product.reviews.all()

    related_products = Product.objects.exclude(
        id=product.id
    ).order_by("?")[:8]

    return render(

        request,

        "shop/product_detail.html",

        {

            "product": product,

            "reviews": reviews,

            "related_products": related_products

        }

    )


# =====================================
# SEARCH SUGGESTIONS
# =====================================

def search_suggestions(request):

    term = request.GET.get(
        "term",
        ""
    )

    products = Product.objects.filter(

        Q(name__icontains=term) |

        Q(category__icontains=term)

    )[:10]

    data = []

    for product in products:

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

def add_to_cart(request, product_id):

    cart = request.session.get(
        "cart",
        {}
    )

    product_id = str(product_id)

    cart[product_id] = (
        cart.get(product_id, 0) + 1
    )

    request.session["cart"] = cart

    return redirect("cart")


def cart_view(request):

    cart = request.session.get(
        "cart",
        {}
    )

    products = []

    total_price = 0

    for product_id, quantity in cart.items():

        try:

            product = Product.objects.get(
                id=product_id
            )

            product.quantity = quantity

            product.subtotal = (
                product.price * quantity
            )

            total_price += (
                product.subtotal
            )

            products.append(product)

        except Product.DoesNotExist:

            pass

    return render(

        request,

        "shop/cart.html",

        {

            "products": products,

            "total_price": total_price

        }

    )


def increase_quantity(
    request,
    product_id
):

    cart = request.session.get(
        "cart",
        {}
    )

    product_id = str(product_id)

    if product_id in cart:

        cart[product_id] += 1

    request.session["cart"] = cart

    return redirect("cart")


def decrease_quantity(
    request,
    product_id
):

    cart = request.session.get(
        "cart",
        {}
    )

    product_id = str(product_id)

    if product_id in cart:

        cart[product_id] -= 1

        if cart[product_id] <= 0:

            del cart[product_id]

    request.session["cart"] = cart

    return redirect("cart")


def remove_from_cart(
    request,
    product_id
):

    cart = request.session.get(
        "cart",
        {}
    )

    product_id = str(product_id)

    if product_id in cart:

        del cart[product_id]

    request.session["cart"] = cart

    return redirect("cart")


def clear_cart(request):

    request.session["cart"] = {}

    return redirect("cart")


# =====================================
# CHECKOUT
# =====================================

def checkout_view(request):

    request.session["cart"] = {}

    return render(
        request,
        "shop/checkout.html"
    )