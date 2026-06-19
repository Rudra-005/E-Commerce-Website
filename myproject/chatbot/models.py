from django.db import models
from django.contrib.auth.models import User


class ProductEmbedding(models.Model):
    """Stores vector embeddings for products (BAAI/bge-small-en-v1.5 = 384 dims)."""

    product = models.OneToOneField(
        'shop.Product',
        on_delete=models.CASCADE,
        related_name='embedding'
    )

    embedding = models.JSONField(
        help_text="384-dim vector from BAAI/bge-small-en-v1.5 as JSON list"
    )

    text_content = models.TextField(
        blank=True,
        help_text="The text that was embedded (for debugging)"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Embedding"
        verbose_name_plural = "Product Embeddings"

    def __str__(self):
        return f"Embedding: {self.product.name}"


class ChatSession(models.Model):
    """Groups chat messages into a conversation session."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_sessions'
    )

    session_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="Django session key for anonymous users"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.user:
            return f"Chat: {self.user.username} ({self.created_at:%Y-%m-%d})"
        return f"Chat: anonymous ({self.created_at:%Y-%m-%d})"


class ChatMessage(models.Model):
    """Individual message within a chat session."""

    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES
    )

    content = models.TextField()

    products_data = models.JSONField(
        default=list,
        blank=True,
        help_text="Products returned with this assistant message"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        preview = self.content[:60]
        return f"[{self.role}] {preview}"
