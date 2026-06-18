from .models import Cart
from django.db.models import Sum

def cart_count(request):
    try:
        total = Cart.objects.aggregate(total=Sum('quantity'))['total'] or 0
    except Exception:
        total = 0
    return {
        'cart_count': total
    }
