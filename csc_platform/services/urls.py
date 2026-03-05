from django.urls import path
from . import views

urlpatterns = [
    # This creates the path: 127.0.0.1:8000/shop/print-n-card/
    path('shop/<slug:shop_slug>/', views.shop_home, name='shop_home'),
]