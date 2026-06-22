from django.contrib import admin
from .models import ProductEmbedding, ChatSession, ChatMessage


@admin.register(ProductEmbedding)
class ProductEmbeddingAdmin(admin.ModelAdmin):
    list_display = ('product', 'updated_at')
    search_fields = ('product__name',)
    readonly_fields = ('embedding', 'text_content', 'updated_at')


class ChatMessageInline(admin.TabularInline):
    """Inline display of messages within a ChatSession."""
    model = ChatMessage
    extra = 0
    readonly_fields = ('role', 'content', 'products_data', 'created_at')
    fields = ('role', 'content', 'created_at')
    ordering = ('created_at',)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'message_count', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('user__username', 'user__email', 'session_key')
    readonly_fields = ('created_at',)
    inlines = [ChatMessageInline]

    def user_display(self, obj):
        if obj.user:
            return f"{obj.user.username} ({obj.user.email})"
        return f"Anonymous ({obj.session_key[:12]}...)" if obj.session_key else "Anonymous"
    user_display.short_description = 'User'
    user_display.admin_order_field = 'user__username'

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'user_display', 'role', 'short_content', 'created_at')
    list_filter = ('role', 'session__user', 'created_at')
    search_fields = ('content', 'session__user__username')
    readonly_fields = ('session', 'role', 'content', 'products_data', 'created_at')

    def user_display(self, obj):
        if obj.session.user:
            return obj.session.user.username
        return "Anonymous"
    user_display.short_description = 'User'
    user_display.admin_order_field = 'session__user__username'

    def short_content(self, obj):
        return obj.content[:80]
    short_content.short_description = 'Content'
