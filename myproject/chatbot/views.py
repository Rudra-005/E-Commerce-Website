"""
REST API views for the AI Shopping Assistant.
Completely isolated — no modifications to existing shop views.
"""

import json
import logging
from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import ChatSession, ChatMessage
from mongodb.chat_repository import (
    create_conversation, 
    save_message, 
    get_user_conversations, 
    get_conversation_messages,
    delete_conversation,
    delete_all_user_conversations,
    rename_conversation
)

logger = logging.getLogger(__name__)


# =====================================
# HELPER FUNCTIONS
# =====================================

def _get_or_create_session(request):
    """Get or create a chat session for the current user/session."""
    if request.user.is_authenticated:
        session, created = ChatSession.objects.get_or_create(
            user=request.user,
            defaults={'session_key': ''}
        )
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        session, created = ChatSession.objects.get_or_create(
            session_key=session_key,
            user=None,
            defaults={}
        )
    return session


def _get_chat_history(session, limit=10):
    """Get recent chat history for context."""
    messages = ChatMessage.objects.filter(session=session).order_by('-created_at')[:limit]
    history = []
    for msg in reversed(messages):
        history.append({
            'role': msg.role,
            'content': msg.content,
        })
    return history


# =====================================
# CHAT API
# =====================================

@method_decorator(csrf_exempt, name="dispatch")
class ChatAPIView(View):
    """
    POST /api/chat/

    Request: { "message": "..." }
    Response: SSE Stream of products and text chunks
    """
    http_method_names = ["post"]

    def post(self, request):
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            # The frontend can send a specific conversation_id for MongoDB
            mongo_conv_id = data.get('conversation_id')

            if not user_message:
                return JsonResponse({'error': 'Message is required.'}, status=400)

            # 1. Get/create PostgreSQL session (keeps existing logic intact)
            session = _get_or_create_session(request)

            # MongoDB Logic: If no conversation_id, create one.
            user_id = request.user.id if request.user.is_authenticated else session.session_key
            if not mongo_conv_id:
                # Use first message as title (truncated)
                title = user_message[:30] + "..." if len(user_message) > 30 else user_message
                mongo_conv_id = create_conversation(user_id=user_id, title=title)

            # 2. Save user message to PostgreSQL
            ChatMessage.objects.create(
                session=session,
                role='user',
                content=user_message,
                products_data=[]
            )
            
            # Save to MongoDB
            if mongo_conv_id:
                save_message(mongo_conv_id, user_id, "user", user_message)

            # 3. Get chat history for context
            chat_history = _get_chat_history(session, limit=10)

            # Strip any SYSTEM OVERRIDE hidden suffix before parsing logic
            import re
            clean_message = re.sub(r'\[SYSTEM OVERRIDE:.*?\]', '', user_message, flags=re.DOTALL).strip()
            msg_lower = clean_message.lower().strip()

            # 4. Bypass vector search if the query is a greeting, or relates to cart, orders, or user profile/account
            greetings = {'hi', 'hii', 'hello', 'hey', 'yo', 'greetings', 'sup', 'hola', 'test', 'help', 'thanks', 'thank you', 'bye', 'goodbye'}
            is_greeting = msg_lower.strip('?.! ') in greetings

            is_cart_query = any(kw in msg_lower for kw in ['cart', 'basket', 'bag', 'subtotal', 'checkout'])
            is_order_query = any(kw in msg_lower for kw in ['track', 'delivery', 'status', 'shipped', 'shipping', 'purchase', 'history', 'return', 'replace', 'cancel', 'refund']) or 'orders' in msg_lower or 'my order' in msg_lower or 'recent order' in msg_lower
            is_account_query = any(kw in msg_lower for kw in ['account', 'profile', 'my info', 'who am i', 'email', 'username'])
            is_address_query = any(kw in msg_lower for kw in ['address', 'addresses', 'location', 'pincode'])

            bypass_search = is_greeting or is_cart_query or is_order_query or is_account_query or is_address_query

            if bypass_search:
                products, filters = [], {}
                logger.info("Non-product query detected (greeting/cart/order/profile/address), skipping vector search")
            else:
                # Vector search for relevant products
                from .services.vector_search import search_products
                products, filters = search_products(clean_message, top_k=8)

            # Generate user account, cart, and order context
            from .services.groq_service import build_user_context
            user_context_str = build_user_context(request.user)

            def event_stream():
                full_text = []
                final_products = products
                try:
                    # Call Groq LLM with streaming enabled
                    from .services.groq_service import get_client, build_context, build_messages
                    client = get_client()
                    product_context = build_context(products, filters)
                    messages = build_messages(chat_history[:-1], user_message, product_context, user_context_str)

                    completion = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1024,
                        top_p=0.9,
                        stream=True,
                    )

                    for chunk in completion:
                        text_chunk = chunk.choices[0].delta.content or ""
                        if text_chunk:
                            full_text.append(text_chunk)
                            yield f"event: content\ndata: {json.dumps(text_chunk)}\n\n"

                    # Filter and re-rank products based on LLM response
                    ai_response = "".join(full_text)
                    ai_response_lower = ai_response.lower()
                    mentioned_products = []

                    for p in products:
                        p_name_lower = p['name'].lower()
                        if p_name_lower in ai_response_lower:
                            mentioned_products.append(p)
                        else:
                            words = p_name_lower.split()
                            matched = False
                            if len(words) >= 3:
                                prefix_3 = " ".join(words[:3])
                                if prefix_3 in ai_response_lower:
                                    mentioned_products.append(p)
                                    matched = True
                            if not matched and len(words) >= 2:
                                prefix_2 = " ".join(words[:2])
                                if prefix_2 in ai_response_lower:
                                    mentioned_products.append(p)
                                    matched = True

                    def get_appearance_index(p):
                        p_name_lower = p['name'].lower()
                        idx = ai_response_lower.find(p_name_lower)
                        if idx != -1:
                            return idx
                        words = p_name_lower.split()
                        if len(words) >= 3:
                            idx = ai_response_lower.find(" ".join(words[:3]))
                            if idx != -1:
                                return idx
                        if len(words) >= 2:
                            idx = ai_response_lower.find(" ".join(words[:2]))
                            if idx != -1:
                                return idx
                        return 999999

                    if mentioned_products:
                        mentioned_products.sort(key=get_appearance_index)
                        final_products = mentioned_products

                    # Send products after text streaming is complete
                    yield f"event: products\ndata: {json.dumps(final_products)}\n\n"

                    yield "event: done\ndata: {}\n\n"
                except Exception as stream_err:
                    import traceback
                    err_str = traceback.format_exc()
                    logger.error(f"Streaming error: {stream_err}\n{err_str}")
                    yield f"event: error\ndata: {json.dumps({'message': 'I encountered an issue processing your request.', 'debug': str(stream_err)})}\n\n"
                finally:
                    # Save assistant response to databases
                    ai_response = "".join(full_text)
                    if ai_response:
                        # PostgreSQL
                        ChatMessage.objects.create(
                            session=session,
                            role='assistant',
                            content=ai_response,
                            products_data=final_products
                        )
                        # MongoDB
                        if mongo_conv_id:
                            save_message(
                                mongo_conv_id, 
                                user_id, 
                                "assistant", 
                                ai_response, 
                                metadata={"products": final_products}
                            )

            response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
            # Pass conversation_id in headers so frontend knows the ID for new chats
            response['X-Conversation-Id'] = mongo_conv_id or ""
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)
        except Exception as e:
            logger.error(f"Chat API error: {e}", exc_info=True)
            return JsonResponse({
                'message': "I'm having a small issue right now. Please try again!",
                'products': [],
            })


# =====================================
# CHAT HISTORY API
# =====================================

class ChatHistoryAPIView(View):
    """
    GET /api/chat/history/

    Returns the current session's chat messages along with the
    current user identifier so the frontend can detect user changes.
    """
    http_method_names = ["get"]

    def get(self, request):
        try:
            # Use current logic as fallback/default
            session = _get_or_create_session(request)
            messages = ChatMessage.objects.filter(session=session).order_by('created_at')

            history = []
            for msg in messages:
                history.append({
                    'role': msg.role,
                    'content': msg.content,
                    'products': msg.products_data or [],
                    'timestamp': msg.created_at.isoformat(),
                })

            current_user = request.user.username if request.user.is_authenticated else None
            
            # Fetch MongoDB conversations to populate the sidebar
            user_id = request.user.id if request.user.is_authenticated else session.session_key
            mongo_conversations = get_user_conversations(user_id)
            
            # Serialize for JSON
            sidebar_convs = []
            for c in mongo_conversations:
                sidebar_convs.append({
                    "id": c.get("conversation_id"),
                    "title": c.get("title", "Chat"),
                    "updated_at": c.get("updated_at").isoformat() if c.get("updated_at") else None
                })

            return JsonResponse({
                'history': history,
                'current_user': current_user,
                'conversations': sidebar_convs
            })

        except Exception as e:
            logger.error(f"Chat history error: {e}", exc_info=True)
            return JsonResponse({'history': [], 'current_user': None, 'conversations': []})


# =====================================
# CHAT HISTORY DELETE API
# =====================================

@method_decorator(csrf_exempt, name="dispatch")
class ChatHistoryDeleteAPIView(View):
    """
    DELETE /api/chat/history/

    Clears the current session's chat history.
    """
    http_method_names = ["delete"]

    def delete(self, request):
        try:
            session = _get_or_create_session(request)
            user_id = request.user.id if request.user.is_authenticated else session.session_key
            
            # Delete PostgreSQL
            ChatMessage.objects.filter(session=session).delete()
            
            # Delete MongoDB
            delete_all_user_conversations(user_id)
            
            return JsonResponse({'status': 'ok', 'message': 'Chat history cleared.'})

        except Exception as e:
            logger.error(f"Chat history delete error: {e}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)


# =====================================
# MONGODB CONVERSATION API
# =====================================

class MongoConversationAPIView(View):
    """
    GET /api/chat/conversations/<id>/
    DELETE /api/chat/conversations/<id>/
    """
    def get(self, request, conv_id):
        msgs = get_conversation_messages(conv_id)
        history = []
        for msg in msgs:
            history.append({
                'role': msg.get('sender'),
                'content': msg.get('message'),
                'products': msg.get('metadata', {}).get('products', []),
                'timestamp': msg.get('timestamp').isoformat() if msg.get('timestamp') else None,
            })
        return JsonResponse({'history': history})

    def delete(self, request, conv_id):
        session = _get_or_create_session(request)
        user_id = request.user.id if request.user.is_authenticated else session.session_key
        delete_conversation(conv_id, user_id)
        return JsonResponse({'status': 'ok'})
