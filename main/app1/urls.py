from .views import ProductDetailView
from django.urls import path

app_name = "products"

urlpatterns = [
    path("<slug>/", ProductDetailView.as_view(), name="product-detail"),
]
