from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from .models import User, Shop, Service, Customer, ServiceRequest, UploadedDocument, Appointment

# ---------------------------------------------------------
# 1. THE SECURITY GUARD (Multi-Tenant Isolation)
# ---------------------------------------------------------
class ShopIsolatedAdmin(ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        # Security for Moderators: Only see shops they onboarded
        if getattr(request.user, 'is_moderator', False):
            if self.model == Shop:
                return qs.filter(onboarded_by=request.user)
            return qs.none() # Mods don't need to see individual customer documents

        # Security for Shop Owners
        if hasattr(request.user, 'shop'):
            if self.model == UploadedDocument:
                return qs.filter(request__shop=request.user.shop)
            elif self.model == Shop:
                return qs.filter(owner=request.user)
            else:
                return qs.filter(shop=request.user.shop)
        return qs.none()

    def save_model(self, request, obj, form, change):
        # Auto-assign the shop to items created by the owner
        if not request.user.is_superuser and hasattr(request.user, 'shop'):
            if hasattr(obj, 'shop'):
                obj.shop = request.user.shop
        
        # Auto-assign the Moderator when they create a shop
        if getattr(request.user, 'is_moderator', False) and self.model == Shop and not change:
            obj.onboarded_by = request.user
            
        super().save_model(request, obj, form, change)

    # SECURE THE DELETE BUTTON
    def has_delete_permission(self, request, obj=None):
        if getattr(request.user, 'is_moderator', False):
            return False # Moderators can NEVER delete. They must Flag.
        return super().has_delete_permission(request, obj)

# ---------------------------------------------------------
# 2. BEAUTIFIED USER DASHBOARD
# ---------------------------------------------------------
# 2. BEAUTIFIED USER DASHBOARD & UNTOUCHABLE ADMIN
# ---------------------------------------------------------
@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    fieldsets = (
        ("Account Credentials", {"fields": ("username", "password")}),
        ("Personal Profile", {"fields": ("first_name", "last_name", "email", "phone_number")}),
        ("Permissions & Roles", {
            "fields": ("is_staff", "is_shop_owner", "is_moderator", "is_superuser"), 
            "description": "Enable 'Staff' along with a role to grant dashboard access automatically."
        }),
    )
    list_display = ['username', 'email', 'is_shop_owner', 'is_moderator', 'is_staff']
    list_filter = ['is_shop_owner', 'is_moderator', 'is_staff']

    # --- NEW: STOP PRIVILEGE ESCALATION ---
    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        # If the user is NOT a superuser, they cannot edit these power checkboxes!
        if not request.user.is_superuser:
            return list(readonly) + ['is_superuser', 'is_staff', 'is_moderator', 'is_shop_owner']
        return readonly

    # --- THE UNTOUCHABLE ADMIN LOCK ---
    def has_change_permission(self, request, obj=None):
        if obj and obj.id == 1 and request.user.id != 1: return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.id == 1: return False
        return super().has_delete_permission(request, obj)
# ---------------------------------------------------------
# 3. REGISTERING ALL MODELS (With Flagship UI)
# ---------------------------------------------------------

@admin.register(Shop)
class ShopAdmin(ShopIsolatedAdmin):
    list_display = ['name', 'owner', 'onboarded_by', 'is_flagged', 'phone', 'view_storefront']
    list_filter = ['is_flagged', 'onboarded_by']
    search_fields = ['name']
    
    def get_readonly_fields(self, request, obj=None):
        if getattr(request.user, 'is_moderator', False):
            return ['onboarded_by'] 
        if not request.user.is_superuser:
            return ['owner', 'slug', 'onboarded_by', 'is_flagged']
        return []

    def view_storefront(self, obj):
        """Generates a clickable link to the public shop page in the admin table."""
        if obj.slug:
            url = reverse('shop_home', args=[obj.slug])
            return format_html('<a href="{}" target="_blank" class="text-blue-600 font-bold hover:underline">View Live Shop ↗</a>', url)
        return "-"
    view_storefront.short_description = "Public Link"

    # --- NEW: SINGLE SHOP UI CONSTRAINT ---
    def has_add_permission(self, request):
        """Hides the 'Add' button if a Shop Owner already has a shop."""
        # Superusers and Moderators can add as many shops as they want
        if request.user.is_superuser or getattr(request.user, 'is_moderator', False):
            return True
            
        # If the user is just a regular Shop Owner...
        if getattr(request.user, 'is_shop_owner', False):
            # Check if they already have a shop linked to their profile
            if hasattr(request.user, 'shop'):
                return False # Hide the "Add Shop" button!
                
        return super().has_add_permission(request)
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
    list_display = ['document_name', 'request', 'uploaded_at', 'secure_download_button']
    
    def secure_download_button(self, obj):
        """Creates a secure download button instead of exposing the raw file link."""
        if obj.file:
            url = reverse('secure_download', args=[obj.id])
            return format_html(
                '<a href="{}" target="_blank" class="text-white bg-green-600 px-3 py-1 rounded text-xs font-bold hover:bg-green-700">↓ Download Securely</a>', 
                url
            )
        return "-"
    secure_download_button.short_description = "Encrypted File"
@admin.register(Appointment)
class AppointmentAdmin(ShopIsolatedAdmin):
    list_display = ['date', 'time_slot', 'customer_name', 'shop']
    list_filter = ['date']
    
    def customer_name(self, obj):
        return obj.request.customer.name if obj.request else "N/A"