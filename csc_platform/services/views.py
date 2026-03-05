from django.shortcuts import render, get_object_or_404, redirect
from .models import Shop, Service, Customer, ServiceRequest, UploadedDocument

def shop_home(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug)
    services = Service.objects.filter(shop=shop, is_active=True)
    return render(request, 'shop_front/shop_home.html', {'shop': shop, 'services': services})

def service_apply(request, shop_slug, service_id):
    shop = get_object_or_404(Shop, slug=shop_slug)
    service = get_object_or_404(Service, id=service_id, shop=shop)

    if request.method == 'POST':
        # 1. Get the form data
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        
        # 2. Find existing customer by phone, or create a new one!
        customer, created = Customer.objects.get_or_create(
            shop=shop, 
            phone_number=phone,
            defaults={'name': name}
        )

        # 3. Create the Service Request
        service_request = ServiceRequest.objects.create(
            shop=shop,
            customer=customer,
            service=service
        )

        # 4. Save uploaded documents securely
        # getlist allows uploading multiple files at once
        documents = request.FILES.getlist('documents')
        for doc in documents:
            UploadedDocument.objects.create(
                request=service_request,
                document_name=doc.name,
                file=doc
            )
        
        # 5. Redirect to the success page with their tracking ID
        return redirect('request_success', shop_slug=shop.slug, tracking_id=service_request.tracking_id)

    # If it's a GET request, just show the blank form
    return render(request, 'shop_front/apply.html', {'shop': shop, 'service': service})

def request_success(request, shop_slug, tracking_id):
    shop = get_object_or_404(Shop, slug=shop_slug)
    service_request = get_object_or_404(ServiceRequest, tracking_id=tracking_id, shop=shop)
    return render(request, 'shop_front/success.html', {'shop': shop, 'service_request': service_request})

def track_status(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug)
    service_request = None
    error_message = None

    if request.method == 'POST':
        tracking_id = request.POST.get('tracking_id')
        phone = request.POST.get('phone')
        
        try:
            # We check both ID and Phone to make sure the right person is looking it up
            service_request = ServiceRequest.objects.get(
                tracking_id=tracking_id, 
                customer__phone_number=phone,
                shop=shop
            )
        except ServiceRequest.DoesNotExist:
            error_message = "No request found with those details. Please check and try again."

    return render(request, 'shop_front/track.html', {
        'shop': shop, 
        'service_request': service_request,
        'error_message': error_message
    })