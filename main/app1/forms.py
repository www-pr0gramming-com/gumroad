from django import forms
from .models import Product


class ProductModelForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "name",
            "descriptioin",
            "cover",
            "slug",
            "content_url",
            "content_file",
            "price",
            "active",
        )
