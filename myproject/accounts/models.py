from django.db import models
from django.contrib.auth.models import User

class SocialAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=50, default='google')  # For future scalability (e.g., github, facebook)
    unique_id = models.CharField(max_length=255, unique=True)    # Mapped directly to Google's persistent 'sub' claim
    extra_data = models.JSONField(blank=True, null=True)          # Keeps a trace history of the raw payload
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('provider', 'unique_id')

    def __str__(self):
        return f"{self.user.email} - {self.provider}"
