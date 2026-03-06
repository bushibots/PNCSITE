import uuid
import secrets
import string
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def generate_tracking_id():
    """Generates a secure, cryptographically random 8-character ID."""
    alphabet = string.ascii_uppercase + string.digits
    # secrets.choice picks a truly random character one by one
    return ''.join(secrets.choice(alphabet) for i in range(8))

def document_upload_path(instance, filename):
    """Saves files securely organized by shop and tracking ID."""
    # Example: media/shops/print-n-card/requests/A1B2C3D4/aadhaar.pdf
    shop_slug = instance.request.shop.slug
    tracking_id = instance.request.tracking_id
    return f"shops/{shop_slug}/requests/{tracking_id}/{filename}"

def validate_file_size(value):
    """Blocks any file larger than 5 Megabytes (5MB)"""
    max_size_mb = 5
    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"File size cannot exceed {max_size_mb}MB.")
    return value
# ---------------------------------------------------------
# CORE MODELS
# ---------------------------------------------------------

class User(AbstractUser):
    """
    Custom user model.
    """
    is_shop_owner = models.BooleanField(default=False)
    is_moderator = models.BooleanField(default=False) # <-- NEW: Moderator Role
    phone_number = models.CharField(max_length=15, blank=True, null=True)

class Shop(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shop')
    
    # --- NEW: Moderator Tracking & Security ---
    onboarded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='onboarded_shops')
    is_flagged = models.BooleanField(default=False, help_text="Check this to report a suspicious shop to the Admin.")
    # ----------------------------------------
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, help_text="Used for the URL, e.g., 'print-n-card'")
    tagline = models.CharField(max_length=200, blank=True)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    opening_time = models.CharField(max_length=20, default="10:00 AM")
    closing_time = models.CharField(max_length=20, default="06:00 PM")

    def __str__(self):
        return self.name

class Service(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=100) # e.g., "PAN Card Application"
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estimated_days = models.IntegerField(default=1, help_text="Estimated processing time in days")
    is_active = models.BooleanField(default=True)

    class Meta:
        # A shop shouldn't have two services with the exact same name
        unique_together = ('shop', 'name')

    def __str__(self):
        return f"{self.name} ({self.shop.name})"

class Customer(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)

    class Meta:
        # Prevent creating duplicate customers for the same shop
        unique_together = ('shop', 'phone_number')

    def __str__(self):
        return f"{self.name} - {self.phone_number}"

class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('DOCS_VERIFIED', 'Documents Verified'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('READY', 'Ready for Pickup'),
    ]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='requests')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='requests')
    service = models.ForeignKey(Service, on_delete=models.RESTRICT) # RESTRICT prevents deleting a service if a request uses it
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    tracking_id = models.CharField(max_length=10, default=generate_tracking_id, unique=True, editable=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tracking_id} - {self.service.name} for {self.customer.name}"

class UploadedDocument(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='documents')
    document_name = models.CharField(max_length=100) # e.g., "Aadhaar Card", "Photo"
    
    # --- NEW: HARDENED FILE FIELD ---
    file = models.FileField(
        upload_to=document_upload_path,
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png']),
            validate_file_size
        ]
    )
    # --------------------------------
    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document_name} for {self.request.tracking_id}"
    
class Appointment(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='appointments')
    request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name='appointment')
    date = models.DateField()
    time_slot = models.CharField(max_length=20) # e.g., "10:30 AM - 11:00 AM"
    
    class Meta:
        # Basic constraint: Only one appointment per time slot per shop
        unique_together = ('shop', 'date', 'time_slot')

    def __str__(self):
        return f"{self.date} at {self.time_slot} - {self.request.customer.name}"
    
    # ---------------------------------------------------------
# AUTOMATION: The Magic Permission Granter
# ---------------------------------------------------------
# ---------------------------------------------------------
# AUTOMATION: The Magic Permission Granter
# ---------------------------------------------------------
@receiver(post_save, sender=User)
def auto_grant_role_permissions(sender, instance, created, **kwargs):
    if not instance.is_staff:
        return # Only staff get dashboard access

    # 1. Give Shop Owners their permissions
    if instance.is_shop_owner:
        models_to_grant = [Shop, Service, Customer, ServiceRequest, UploadedDocument, Appointment]
        permissions_to_add = []
        for model in models_to_grant:
            content_type = ContentType.objects.get_for_model(model)
            permissions = Permission.objects.filter(content_type=content_type)
            permissions_to_add.extend(permissions)
        instance.user_permissions.add(*permissions_to_add)

    # 2. Give Moderators their restricted permissions (NO DELETE POWER)
    if instance.is_moderator:
        models_to_grant = [Shop, User] # They only need to manage Shops and create Users
        permissions_to_add = []
        for model in models_to_grant:
            content_type = ContentType.objects.get_for_model(model)
            # Fetch permissions but EXCLUDE any "delete" permissions
            permissions = Permission.objects.filter(content_type=content_type).exclude(codename__startswith='delete_')
            permissions_to_add.extend(permissions)
        instance.user_permissions.add(*permissions_to_add)