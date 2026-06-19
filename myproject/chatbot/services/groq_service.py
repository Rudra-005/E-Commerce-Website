"""
Groq LLM service using llama-3.3-70b-versatile.
Handles prompt engineering, context building, and response generation.
"""

import os
import json
import logging
from groq import Groq

logger = logging.getLogger(__name__)

# Lazy-loaded singleton client
_client = None


def get_client():
    """Get the Groq client (singleton)."""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            from django.conf import settings
            api_key = getattr(settings, 'GROQ_API_KEY', None)
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables or settings.")
        _client = Groq(api_key=api_key, timeout=10.0)
    return _client


SYSTEM_PROMPT = """You are Velora AI Shopping Assistant.

You help users discover products, check their active cart, track their recent orders, get account details, and check their saved addresses.

RULES:
1. You have direct access to the user's profile, saved addresses, active cart, and order history (in the system context below).
2. If the user asks about their cart (e.g. what's in it, total price, quantity), look at CURRENT CART ITEMS and summarize it.
3. If they ask about their orders (e.g. order status, tracking, previous purchases), look at RECENT ORDERS.
4. NEVER invent or hallucinate products. Only recommend products from the RETRIEVED PRODUCTS list below.
5. Explain WHY each product matches the user's needs using product attributes (price, category, description, rating).
6. Keep answers concise, helpful, and friendly.
7. If no relevant products are found in the catalog, but they asked about their cart, orders, profile, or addresses, answer those questions directly.
8. If the user asks about completely off-topic subjects (not shopping, cart, orders, profile, or addresses), politely redirect: "I'm specialized in helping you find great products and manage your account at Velora!"
9. Use plain text with line breaks. Do NOT use markdown like ** or ## or *. For product names or headings, just write them normally.
10. If the user asks about their saved addresses, look at SAVED ADDRESSES and list or summarize them clearly."""


def build_context(products, filters=None):
    """Build the product context string for the LLM."""
    if not products:
        return "RETRIEVED PRODUCTS: None found matching the query."

    lines = ["RETRIEVED PRODUCTS:"]
    for i, p in enumerate(products, 1):
        lines.append(
            f"\n{i}. {p['name']}"
            f"\n   Price: ₹{p['price']}"
            f"\n   Category: {p.get('category', 'N/A')}"
            f"\n   Rating: {p.get('rating', 'N/A')}/5"
            f"\n   Stock: {p.get('stock', 'N/A')}"
            f"\n   Description: {p.get('description', '')}"
        )

    if filters:
        lines.append(f"\nUSER FILTERS DETECTED: {json.dumps(filters)}")

    return "\n".join(lines)


def build_user_context(user):
    """Build the user account, cart, and order context string."""
    if not user or not user.is_authenticated:
        return "CURRENT USER: Anonymous (Not logged in)."

    lines = [f"CURRENT USER: {user.first_name or user.username} (Email: {user.email})"]

    # 1. Profile Info (phone, date of birth)
    try:
        from shop.models import UserProfile
        profile = UserProfile.objects.filter(user=user).first()
        if profile:
            if profile.phone:
                lines.append(f"Profile Phone: {profile.phone}")
            if profile.date_of_birth:
                lines.append(f"Profile Date of Birth: {profile.date_of_birth.strftime('%B %d, %Y')}")
    except Exception as e:
        logger.error(f"Error retrieving profile info in build_user_context: {e}")

    # 2. Saved Addresses
    try:
        from shop.models import Address, UserProfile
        profile = UserProfile.objects.filter(user=user).first()
        if profile:
            addresses = Address.objects.filter(user_profile=profile)
            if addresses.exists():
                lines.append("\nSAVED ADDRESSES:")
                for i, addr in enumerate(addresses, 1):
                    addr_str = f"- Address {i}: {addr.full_name}, Phone: {addr.phone}, {addr.address_line_1}"
                    if addr.address_line_2:
                        addr_str += f", {addr.address_line_2}"
                    addr_str += f", {addr.city}, {addr.state} - {addr.pincode}"
                    if addr.is_default:
                        addr_str += " (Default)"
                    lines.append(addr_str)
            else:
                lines.append("\nSAVED ADDRESSES: No saved addresses found.")
        else:
            lines.append("\nSAVED ADDRESSES: User has no profile details.")
    except Exception as e:
        lines.append(f"\nSAVED ADDRESSES: Error retrieving addresses ({e}).")

    # 3. Cart Items
    try:
        from shop.models import Cart
        cart_items = Cart.objects.filter(user=user).select_related('product')
        if cart_items.exists():
            lines.append("\nCURRENT CART ITEMS:")
            total_cart_price = 0
            for i, item in enumerate(cart_items, 1):
                subtotal = item.product.price * item.quantity
                total_cart_price += subtotal
                lines.append(f"- {item.product.name} x {item.quantity} (Price: ₹{item.product.price}, Subtotal: ₹{subtotal})")
            lines.append(f"Total Cart Subtotal: ₹{total_cart_price}")
        else:
            lines.append("\nCURRENT CART ITEMS: Your cart is empty.")
    except Exception as e:
        lines.append(f"\nCURRENT CART ITEMS: Error retrieving cart ({e}).")

    # 4. Recent Orders
    try:
        from shop.models import Order
        orders = Order.objects.filter(user=user).order_by('-created_at')[:3]
        if orders.exists():
            lines.append("\nRECENT ORDERS:")
            for order in orders:
                items_str = ", ".join(f"{item.product.name} x {item.quantity}" for item in order.items.all())
                lines.append(f"- Order #{order.id} on {order.created_at:%Y-%m-%d}: Status: {order.status}, Total: ₹{order.total_price}, Items: [{items_str}]")
        else:
            lines.append("\nRECENT ORDERS: No order history found.")
    except Exception as e:
        lines.append(f"\nRECENT ORDERS: Error retrieving orders ({e}).")

    return "\n".join(lines)


def build_messages(chat_history, user_message, product_context, user_context=""):
    """
    Build the full message list for Groq.
    Includes system prompt, last N history messages, product context, and new user message.
    """
    system_content = SYSTEM_PROMPT
    if user_context:
        system_content += f"\n\n{user_context}"

    messages = [
        {"role": "system", "content": system_content}
    ]

    # Add recent chat history (last 10 messages for memory)
    for msg in chat_history[-10:]:
        messages.append({
            "role": msg['role'],
            "content": msg['content']
        })

    # Add context + user message
    augmented_message = f"{product_context}\n\nUSER QUERY: {user_message}"
    messages.append({
        "role": "user",
        "content": augmented_message
    })

    return messages


def generate_response(user_message, products, filters=None, chat_history=None, user=None):
    """
    Generate an AI response using Groq.

    Args:
        user_message: The user's query
        products: List of retrieved product dicts
        filters: Extracted query filters
        chat_history: List of {role, content} dicts
        user: Optional Django user object

    Returns:
        str: The AI response text
    """
    client = get_client()

    product_context = build_context(products, filters)
    user_context = build_user_context(user)
    history = chat_history or []
    messages = build_messages(history, user_message, product_context, user_context)

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            top_p=0.9,
        )

        response_text = completion.choices[0].message.content
        return response_text

    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return (
            "I'm having trouble connecting right now. "
            "Please try again in a moment!"
        )
