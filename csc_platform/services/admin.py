from django.contrib import admin
from .models import User, Shop, Service, Customer, ServiceRequest, UploadedDocument, Appointment

admin.site.register(User)
admin.site.register(Shop)
admin.site.register(Service)
admin.site.register(Customer)
admin.site.register(ServiceRequest)
admin.site.register(UploadedDocument)
admin.site.register(Appointment)