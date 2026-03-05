from django.urls import path
from . import views

from django.urls import path
from . import views

urlpatterns = [
    path('shop/<slug:shop_slug>/', views.shop_home, name='shop_home'),
    path('shop/<slug:shop_slug>/apply/<int:service_id>/', views.service_apply, name='service_apply'),
    path('shop/<slug:shop_slug>/success/<str:tracking_id>/', views.request_success, name='request_success'),
    
    # New URL for tracking status
    path('shop/<slug:shop_slug>/track/', views.track_status, name='track_status'),
]