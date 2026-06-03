from django.shortcuts import (
    render,
    get_object_or_404,
    redirect
)

from django.http import JsonResponse

from django.core.paginator import Paginator
from django.db.models import Avg, Q
from .models import Product, Category, Review

def home(request):

    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "").strip()
    sort_by = request.GET.get("sort", "")
    page_number = request.GET.get("page", 1)

    featured_products = Product.objects.order_by("?")[:20]

    # BASE QUERYSET
    products_queryset = Product.objects.all()

    # CATEGORY FILTER
    if category:
        products_queryset = products_queryset.filter(
            category_fk__name=category
        )

    # SEARCH FILTER
    if search:
        products_queryset = products_queryset.filter(
            Q(name__icontains=search) |
            Q(category__icontains=search)
        )

    # SORTING
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

    categories = Category.objects.all()

    context = {
        "products": products,
        "featured_products": featured_products,
        "categories": categories,
        "search": search,
        "selected_category": category,
        "sort_by": sort_by,
    }

    return render(
        request,
        "shop/home.html",
        context
    )

    # AJAX REQUEST
    if request.headers.get(
        "X-Requested-With"
    ) == "XMLHttpRequest":

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
            "category": category,
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