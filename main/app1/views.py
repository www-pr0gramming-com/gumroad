from django.shortcuts import redirect
from django.urls import reverse
from django.views import generic
from .models import Product, PurchasedProduct
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import ProductModelForm


import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


from django.shortcuts import get_object_or_404

from django.http import HttpResponse

from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth import get_user_model

User = get_user_model()

from django.core.mail import send_mail


class ProductListView(generic.ListView):
    template_name = "discover.html"
    queryset = Product.objects.filter(active=True)


class ProductDetailView(generic.DetailView):
    template_name = "products/product.html"
    queryset = Product.objects.all()
    queryset_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super(ProductDetailView, self).get_context_data(**kwargs)
        product = self.get_object()
        has_access = False
        if self.request.user.is_authenticated:
            if product in self.request.user.userlibrary.products.all():
                has_access = True
        context.update(
            {
                "has_access": has_access,
            }
        )
        return context


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

        customer = None
        customer_email = None

        if request.user.is_authenticated:
            if request.user.stripe_customer_id:
                customer = request.user.stripe_customer_id
            else:
                customer_email = request.user.email

        product_image_urls = []
        if product.cover:
            if not settings.DEBUG:
                product_image_urls.append(domain + product.cover.url)

        try:
            checkout_session = stripe.checkout.Session.create(
                customer=customer,
                customer_email=customer_email,
                line_items=[
                    {
                        "price_data": {
                            "currency": "jpy",
                            "product_data": {
                                "name": product.name,
                                # "images": [
                                #     "https://cdn.pixabay.com/photo/2015/04/23/22/00/tree-736885_1280.jpg"
                                # ],
                                "images": product_image_urls,
                            },
                            "unit_amount": product.price,
                        },
                        "quantity": 1,
                    }
                ],
                payment_intent_data={
                    "application_fee_amount": 100,
                    "transfer_data": {
                        "destination": product.user.stripe_account_id,
                    },
                },
                mode="payment",
                success_url=domain + reverse("success"),
                cancel_url=domain + reverse("discover"),
                metadata={
                    "product_id": product.pk,
                },
            )
        except Exception as e:
            return str(e)

        return redirect(checkout_session.url, code=303)


@csrf_exempt
def stripe_webhook(request, *args, **kwargs):
    event = None
    payload = request.body
    sig_header = request.headers["STRIPE_SIGNATURE"]
    endpoint_secret = ""

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

    # Handle the event
    if event["type"] == "checkout.session.completed":
        product_id = event["data"]["object"]["metadata"]["product_id"]
        product = Product.objects.get(id=product_id)

        stripe_customer_id = event["data"]["object"]["customer"]

        try:
            user = User.objects.get(stripe_customer_id=stripe_customer_id)
            user.userlibrary.products.add(product)
            print("stripe_customer_id ok")

        except User.DoesNotExist:
            stripe_customer_email = event["data"]["object"]["customer_details"]["email"]
            print("stripe_customer_id not ok")

            try:
                user = User.objects.get(email=stripe_customer_email)
                user.stripe_customer_id = stripe_customer_id
                user.save()
                user.userlibrary.products.add(product)

            except User.DoesNotExist:
                print("no account")

                PurchasedProduct.objects.create(
                    email=stripe_customer_email, product=product
                )

                send_mail(
                    subject="You can access your content",
                    message="Please signup",
                    recipient_list=[stripe_customer_email],
                    from_email="test@test.com",
                )

    elif event["type"] == "account.updated":
        print(event)

    else:
        print("Unhandled event type {}".format(event["type"]))

    return HttpResponse()
