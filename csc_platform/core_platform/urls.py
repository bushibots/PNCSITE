from django.contrib import admin
from django.urls import path, include # <-- We added include here

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('services.urls')), # <-- This routes traffic to your app
]