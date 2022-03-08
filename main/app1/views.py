from django.shortcuts import redirect
from django.urls import reverse
from django.views import generic
from .models import Product
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import ProductModelForm


class ProductListView(generic.ListView):
    template_name = "discover.html"
    queryset = Product.objects.all()


class ProductDetailView(generic.DetailView):
    template_name = "products/product.html"
    queryset = Product.objects.all()
    queryset_object_name = "product"


class UserProductListView(LoginRequiredMixin, generic.ListView):
    template_name = "products.html"

    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)


class ProductCreateView(LoginRequiredMixin, generic.CreateView):
    template_name = "products/product_create.html"
    form_class = ProductModelForm

    def get_success_url(self):
        # print(self.product)
        # return reverse("user-products")
        return reverse("products:product-detail", kwargs={"slug": self.product.slug})

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.user = self.request.user
        instance.save()
        # return redirect("", )
        self.product = instance
        return super(ProductCreateView, self).form_valid(form)
