from django.urls import path
from . import views

urlpatterns = [
    path('shop/<slug:shop_slug>/', views.shop_home, name='shop_home'),
    
    # New URL for the application form
    path('shop/<slug:shop_slug>/apply/<int:service_id>/', views.service_apply, name='service_apply'),
    
    # New URL for the success page
    path('shop/<slug:shop_slug>/success/<str:tracking_id>/', views.request_success, name='request_success'),
]