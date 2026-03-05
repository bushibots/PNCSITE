from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from django.shortcuts import redirect
from django.urls import reverse
from .models import User, Shop, Service, Customer, ServiceRequest, UploadedDocument, Appointment

# ---------------------------------------------------------
# 1. THE SECURITY GUARD (Multi-Tenant Isolation)
# ---------------------------------------------------------
class ShopIsolatedAdmin(ModelAdmin):
    """
    Ensures Shop Owners ONLY see their own data.
    Superusers see everything.
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        # Security: Filter by the shop owned by the current user
        if hasattr(request.user, 'shop'):
            if self.model == UploadedDocument:
                return qs.filter(request__shop=request.user.shop)
            elif self.model == Shop:
                return qs.filter(owner=request.user)
            else:
                return qs.filter(shop=request.user.shop)
        return qs.none()

    def save_model(self, request, obj, form, change):
        """Automatically assign the shop to new items if created by an owner"""
        if not request.user.is_superuser and hasattr(request.user, 'shop'):
            if hasattr(obj, 'shop'):
                obj.shop = request.user.shop
        super().save_model(request, obj, form, change)

# ---------------------------------------------------------
# 2. BEAUTIFIED USER DASHBOARD
# ---------------------------------------------------------
@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    fieldsets = (
        ("Account Credentials", {"fields": ("username", "password")}),
        ("Personal Profile", {"fields": ("first_name", "last_name", "email", "phone_number")}),
        ("Permissions & Roles", {
            "fields": ("is_staff", "is_shop_owner", "is_superuser"),
            "description": "Enable 'Staff' and 'Shop Owner' to grant dashboard access automatically."
        }),
    )
    list_display = ['username', 'email', 'is_shop_owner', 'is_staff']
    list_filter = ['is_shop_owner', 'is_staff']

# ---------------------------------------------------------
# 3. REGISTERING ALL MODELS (With Flagship UI)
# ---------------------------------------------------------

@admin.register(Shop)
class ShopAdmin(ShopIsolatedAdmin):
    list_display = ['name', 'owner', 'phone', 'opening_time']
    search_fields = ['name']
    # If not admin, they shouldn't be able to change the owner or slug
    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return ['owner', 'slug']
        return []

@admin.register(Service)
class ServiceAdmin(ShopIsolatedAdmin):
    list_display = ['name', 'shop', 'price', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']

@admin.register(Customer)
class CustomerAdmin(ShopIsolatedAdmin):
    list_display = ['name', 'phone_number', 'shop']
    search_fields = ['name', 'phone_number']

@admin.register(ServiceRequest)
class ServiceRequestAdmin(ShopIsolatedAdmin):
    list_display = ['tracking_id', 'service', 'customer', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    readonly_fields = ['tracking_id', 'created_at']
    search_fields = ['tracking_id', 'customer__name']

@admin.register(UploadedDocument)
class UploadedDocumentAdmin(ShopIsolatedAdmin):
    list_display = ['document_name', 'request', 'uploaded_at']

@admin.register(Appointment)
class AppointmentAdmin(ShopIsolatedAdmin):
    list_display = ['date', 'time_slot', 'customer_name', 'shop']
    list_filter = ['date']
    
    def customer_name(self, obj):
        return obj.request.customer.name if obj.request else "N/A"