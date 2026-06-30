from .models import Cart, UserProfile
from django.db.models import Sum


def cart_count(request):
    if request.user.is_authenticated:
        try:
            total = Cart.objects.filter(user=request.user).count()
        except Exception:
            total = 0
    else:
        total = 0

    # User avatar/profile image context
    user_avatar_emoji = '🥷'
    user_avatar_url = None
    user_profile = None

    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.profile_image:
                user_avatar_url = user_profile.profile_image.url
            user_avatar_emoji = user_profile.display_avatar
        except UserProfile.DoesNotExist:
            pass

    return {
        'cart_count': total,
        'user_avatar_url': user_avatar_url,
        'user_avatar_emoji': user_avatar_emoji,
        'user_profile_obj': user_profile,
    }
