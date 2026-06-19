from .models import Cart
from django.db.models import Sum

def cart_count(request):
    if request.user.is_authenticated:
        try:
            total = Cart.objects.filter(user=request.user).count()
        except Exception:
            total = 0
    else:
        total = 0
    return {
        'cart_count': total
    }

