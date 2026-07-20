import razorpay
import hmac
import hashlib
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from shop.models import SubscriptionPlan, UserSubscription

# Initialize Razorpay Client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def get_active_subscription(user):
    """
    Returns the currently active subscription for a user, or None.
    """
    if not user.is_authenticated:
        return None
    
    subscription = UserSubscription.objects.filter(
        user=user,
        status='ACTIVE'
    ).first()
    
    if subscription:
        # Check if expired based on end_date
        if subscription.end_date and subscription.end_date < timezone.now():
            subscription.status = 'EXPIRED'
            subscription.save()
            return None
        return subscription
    return None

def calculate_subscription_benefits(cart_total, user):
    """
    Calculates the benefits (shipping and membership discount)
    Returns a dictionary with discount details.
    """
    benefits = {
        'subscription_used': False,
        'membership_discount': Decimal('0.00'),
        'shipping_charge': Decimal('50.00'), # Default shipping
        'shipping_discount': Decimal('0.00'),
        'final_total': Decimal(str(cart_total))
    }
    
    if cart_total == 0:
        benefits['shipping_charge'] = Decimal('0.00')
        return benefits

    subscription = get_active_subscription(user)
    if subscription and subscription.subscription_plan:
        plan = subscription.subscription_plan
        benefits['subscription_used'] = True
        
        # Calculate discount
        if plan.discount_percentage > 0:
            discount = (Decimal(str(cart_total)) * plan.discount_percentage) / Decimal('100.0')
            benefits['membership_discount'] = discount.quantize(Decimal('0.01'))
            benefits['final_total'] -= benefits['membership_discount']
        
        # Free delivery
        if plan.free_delivery:
            benefits['shipping_discount'] = benefits['shipping_charge']
            benefits['shipping_charge'] = Decimal('0.00')
            
    return benefits

def create_razorpay_subscription(user, plan_id):
    """
    Creates a subscription in Razorpay and DB.
    plan_id is the ID of the SubscriptionPlan model.
    """
    plan = SubscriptionPlan.objects.get(id=plan_id)
    
    # Check if user already has an active subscription
    active_sub = get_active_subscription(user)
    if active_sub:
        raise ValueError("User already has an active subscription.")

    # Create Razorpay subscription
    razorpay_subscription = client.subscription.create({
        "plan_id": plan.razorpay_plan_id,
        "total_count": 12 if plan.billing_cycle == 'monthly' else 5,
        "customer_notify": 1,
    })
    
    # Create DB record
    user_sub = UserSubscription.objects.create(
        user=user,
        subscription_plan=plan,
        razorpay_subscription_id=razorpay_subscription['id'],
        status='PENDING'
    )
    
    return user_sub, razorpay_subscription

def verify_razorpay_signature(payload_body, razorpay_signature):
    """
    Verifies Razorpay webhook signature.
    """
    secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
    if not secret:
        return False
        
    generated_signature = hmac.new(
        secret.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(generated_signature, razorpay_signature)

def cancel_subscription(user_subscription_id):
    """
    Cancels a subscription via Razorpay API and updates DB.
    """
    subscription = UserSubscription.objects.get(id=user_subscription_id)
    if subscription.razorpay_subscription_id:
        try:
            client.subscription.cancel(subscription.razorpay_subscription_id)
            subscription.status = 'CANCELLED'
            subscription.cancel_at_cycle_end = True
            subscription.save()
            return True
        except Exception as e:
            # Handle error
            return False
    return False

def sync_subscription_status(razorpay_subscription_id):
    """
    Syncs DB status with Razorpay status.
    """
    try:
        sub = client.subscription.fetch(razorpay_subscription_id)
        db_sub = UserSubscription.objects.filter(razorpay_subscription_id=razorpay_subscription_id).first()
        
        if not db_sub:
            return None
            
        status_map = {
            'created': 'PENDING',
            'authenticated': 'PENDING',
            'active': 'ACTIVE',
            'pending': 'PENDING',
            'halted': 'PAUSED',
            'cancelled': 'CANCELLED',
            'completed': 'EXPIRED',
            'expired': 'EXPIRED'
        }
        
        rzp_status = sub.get('status', '')
        if rzp_status in status_map:
            db_sub.status = status_map[rzp_status]
            
        # Update dates if available
        if sub.get('current_start'):
            db_sub.start_date = timezone.datetime.fromtimestamp(sub['current_start'], tz=timezone.utc)
        if sub.get('current_end'):
            db_sub.end_date = timezone.datetime.fromtimestamp(sub['current_end'], tz=timezone.utc)
            
        db_sub.save()
        return db_sub
    except Exception as e:
        return None
