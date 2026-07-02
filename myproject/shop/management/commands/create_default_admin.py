from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from shop.models import UserProfile

class Command(BaseCommand):
    help = 'Creates a default admin account with full permissions.'

    def handle(self, *args, **kwargs):
        email = 'ADMIN_EMAIL' # Change this before production
        password = 'ADMIN_PASSWORD'
        
        user, created = User.objects.get_or_create(username='admin', defaults={'email': email})
        
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created new admin user with username: admin'))
        else:
            self.stdout.write(self.style.WARNING(f'Admin user already exists. Updating permissions...'))

        profile, profile_created = UserProfile.objects.get_or_create(user=user)
        
        profile.role = 'admin'
        profile.permissions = [
            "dashboard", "chat", "orders", "products", 
            "users", "analytics", "refunds", "settings"
        ]
        profile.save()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully assigned admin role and permissions to: admin'))
