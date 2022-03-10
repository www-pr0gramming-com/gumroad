from django.shortcuts import redirect
from django.urls import reverse
from django.views import generic
from .models import Product
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import ProductModelForm


import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


from django.shortcuts import get_object_or_404

from django.http import HttpResponse

from django.views.decorators.csrf import csrf_exempt


class ProductListView(generic.ListView):
    template_name = "discover.html"
    queryset = Product.objects.filter(active=True)


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


class ProductUpdateView(LoginRequiredMixin, generic.UpdateView):
    template_name = "products/product_update.html"
    form_class = ProductModelForm

    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse(
            "products:product-detail", kwargs={"slug": self.get_object().slug}
        )


class ProductDeleteView(LoginRequiredMixin, generic.DeleteView):
    template_name = "products/product_delete.html"

    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse("user-products")


class CreateCheckoutSessionView(generic.View):
    def post(self, request, *args, **kwargs):
        product = get_object_or_404(Product, slug=self.kwargs["slug"])

        domain = "https://domain.com"

        if settings.DEBUG:
            domain = "http://127.0.0.1:8000"

        try:
            checkout_session = stripe.checkout.Session.create(
                line_items=[
                    {
                        "price_data": {
                            "currency": "jpy",
                            "product_data": {
                                "name": product.name,
                                # "images": product.cover.url,
                            },
                            "unit_amount": product.price,
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=domain + reverse("success"),
                cancel_url=domain + reverse("discover"),
            )
        except Exception as e:
            return str(e)

        return redirect(checkout_session.url, code=303)


@csrf_exempt
def stripe_webhook(request, *args, **kwargs):
    event = None
    payload = request.body
    sig_header = request.headers["STRIPE_SIGNATURE"]
    endpoint_secret = "whsec_aRnn8IM5KB0rWjvosjEEJsk1cqXfdiE7"

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)

    except ValueError as e:
        # Invalid payload
        print(e)
        return HttpResponse(status=400)

    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(e)
        return HttpResponse(status=400)

    print(event)

    # # Handle the event
    # if event["type"] == "checkout.session.completed":
    #     session = event["data"]["object"]

    # # ... handle other event types
    # else:
    #     print("Unhandled event type {}".format(event["type"]))

    return HttpResponse()
