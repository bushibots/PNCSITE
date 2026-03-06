from django.shortcuts import render, get_object_or_404, redirect
from .models import Shop, Service, Customer, ServiceRequest, UploadedDocument, Appointment
import os
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseForbidden

# --- NEW IMPORTS FOR THE APPOINTMENT SYSTEM ---
import json
from datetime import datetime, timedelta, date
def shop_home(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug)
    services = Service.objects.filter(shop=shop, is_active=True)
    return render(request, 'shop_front/shop_home.html', {'shop': shop, 'services': services})

def service_apply(request, shop_slug, service_id):
    shop = get_object_or_404(Shop, slug=shop_slug)
    service = get_object_or_404(Service, id=service_id, shop=shop)

    # --- THE SMART SLOT GENERATOR ---
    fmt = "%I:%M %p"
    try:
        open_time = datetime.strptime(shop.opening_time, fmt)
        close_time = datetime.strptime(shop.closing_time, fmt)
    except ValueError:
        # Fallback if the shop owner typed the time wrong
        open_time = datetime.strptime("10:00 AM", fmt)
        close_time = datetime.strptime("06:00 PM", fmt)

    all_slots = []
    current = open_time
    while current < close_time:
        next_time = current + timedelta(minutes=30)
        if next_time > close_time: break
        all_slots.append(f"{current.strftime(fmt)} - {next_time.strftime(fmt)}")
        current = next_time

    # Generate availability for the next 7 days
    today = date.today()
    availability = {}
    for i in range(1, 8): # Tomorrow and the next 6 days
        target_date = today + timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")
        
        # Check database for booked slots on this specific day
        booked = Appointment.objects.filter(shop=shop, date=target_date).values_list('time_slot', flat=True)
        available = [s for s in all_slots if s not in booked]
        availability[date_str] = available

    availability_json = json.dumps(availability)
    # --------------------------------

    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        apt_date = request.POST.get('appointment_date')
        apt_time = request.POST.get('appointment_time')
        
        customer, created = Customer.objects.get_or_create(
            shop=shop, 
            phone_number=phone,
            defaults={'name': name}
        )

        service_request = ServiceRequest.objects.create(
            shop=shop,
            customer=customer,
            service=service
        )

        # --- SAVE THE APPOINTMENT ---
        if apt_date and apt_time:
            Appointment.objects.create(
                shop=shop, 
                request=service_request, 
                date=apt_date, 
                time_slot=apt_time
            )
        # ----------------------------

        documents = request.FILES.getlist('documents')
        for doc in documents:
            UploadedDocument.objects.create(
                request=service_request,
                document_name=doc.name,
                file=doc
            )
        
        return redirect('request_success', shop_slug=shop.slug, tracking_id=service_request.tracking_id)

    # If it's a GET request, pass the schedule to the HTML
    return render(request, 'shop_front/apply.html', {
        'shop': shop, 
        'service': service,
        'availability_json': availability_json # <-- THIS IS WHAT WAS MISSING!
    })

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

# ---------------------------------------------------------
# SECURITY: The Private Document Vault
# ---------------------------------------------------------
def secure_document_download(request, document_id):
    # 1. Bouncer Check 1: Are you even logged in?
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Vault Access Denied: You must be logged in.")

    document = get_object_or_404(UploadedDocument, id=document_id)
    shop = document.request.shop

    # 2. Bouncer Check 2: Are you the Admin or the Shop Owner?
    # Moderators cannot see sensitive customer documents!
    if not (request.user.is_superuser or request.user == shop.owner):
        return HttpResponseForbidden("Vault Access Denied: This document belongs to another shop.")

    # 3. If they pass the checks, securely hand them the file
    file_path = os.path.join(settings.MEDIA_ROOT, document.file.name)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'))
    else:
        raise Http404("Document not found in the vault.")