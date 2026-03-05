import uuid
import random
import string
from django.db import models
from django.contrib.auth.models import AbstractUser

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def generate_tracking_id():
    """Generates a short, readable 8-character ID for customers to track requests."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def document_upload_path(instance, filename):
    """Saves files securely organized by shop and tracking ID."""
    # Example: media/shops/print-n-card/requests/A1B2C3D4/aadhaar.pdf
    shop_slug = instance.request.shop.slug
    tracking_id = instance.request.tracking_id
    return f"shops/{shop_slug}/requests/{tracking_id}/{filename}"

# ---------------------------------------------------------
# CORE MODELS
# ---------------------------------------------------------

class User(AbstractUser):
    """
    Custom user model. Always do this in Django before your first migration.
    It allows us to easily add roles later (e.g., Staff vs Shop Owner).
    """
    is_shop_owner = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

class Shop(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shop')
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, help_text="Used for the URL, e.g., 'print-n-card'")
    tagline = models.CharField(max_length=200, blank=True)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    # Simple text fields for MVP. We can make these complex TimeFields later.
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
    file = models.FileField(upload_to=document_upload_path)
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