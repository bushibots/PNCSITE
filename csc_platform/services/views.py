from django.shortcuts import render, get_object_or_404
from .models import Shop, Service

def shop_home(request, shop_slug):
    # Find the shop by its URL slug (e.g., 'print-n-card') or show a 404 error
    shop = get_object_or_404(Shop, slug=shop_slug)
    
    # Get all active services that belong ONLY to this specific shop
    services = Service.objects.filter(shop=shop, is_active=True)
    
    context = {
        'shop': shop,
        'services': services
    }
    return render(request, 'shop_front/shop_home.html', context)