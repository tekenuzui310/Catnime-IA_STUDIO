from django.urls import path
from .views import health, upscale_image

urlpatterns = [
    path("health/", health, name="health"),
    path("upscale/", upscale_image, name="upscale"),
]
