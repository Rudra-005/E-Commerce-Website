import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User
from shop.models import ShippingAddress

# Find all users that are not superusers
users_to_delete = User.objects.filter(is_superuser=False)

print(f"Found {users_to_delete.count()} non-superuser(s) to delete.")

for user in users_to_delete:
    print(f"Deleting user: {user.username}")
    user.delete()

# Also delete any ShippingAddress records not associated with a user, just in case
orphaned_addresses = ShippingAddress.objects.filter(user__isnull=True)
print(f"Found {orphaned_addresses.count()} orphaned shipping addresses.")
for address in orphaned_addresses:
    address.delete()

print("Deletion complete.")
