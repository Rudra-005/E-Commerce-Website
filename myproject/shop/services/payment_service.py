import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

class PaymentService:
    """Service to handle payment-related business logic."""

    COD_MAX_LIMIT = Decimal('50000.00')
    RESTRICTED_CATEGORIES = ['digital', 'gift card', 'gift-card', 'software', 'ebook', 'gift']

    @staticmethod
    def validate_cod_eligibility(cart_items, address=None):
        """
        Validates if the current order context is eligible for Cash on Delivery.
        Returns a tuple: (is_eligible: bool, reason: str)
        """
        # 1. Check Cart Empty
        if not cart_items or not cart_items.exists():
            return False, "Cart is empty."

        # 2. Check Order Value Limit
        total_price = sum(item.subtotal for item in cart_items)
        if total_price > PaymentService.COD_MAX_LIMIT:
            return False, f"Cash on Delivery is not available for orders above ₹{PaymentService.COD_MAX_LIMIT:,.0f}."

        # 3. Check Restricted Categories (Digital / Gift Cards)
        for item in cart_items:
            category_name = (item.product.category or "").lower()
            if any(restricted in category_name for restricted in PaymentService.RESTRICTED_CATEGORIES):
                return False, f"Cash on Delivery is not available for {item.product.name} (Digital/Gift Card)."

        # 4. Check PIN Code Serviceability (Mock Implementation)
        if address:
            # In a real-world scenario, this would check against a courier API (e.g., Delhivery, BlueDart)
            # For demonstration, we restrict a dummy PIN code.
            if address.pincode == '000000':
                return False, f"Cash on Delivery is not available for PIN Code {address.pincode}."

        return True, "Eligible for Cash on Delivery"
