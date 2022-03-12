from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django.db import models
from main.app1.models import Product

from django.db.models.signals import post_save

from main.app1.models import Product, PurchasedProduct

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class User(AbstractUser):
    """
    Default custom user model for Main.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    #: First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore
    last_name = None  # type: ignore
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_account_id = models.CharField(max_length=100)

    def get_absolute_url(self):
        """Get url for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})


class UserLibrary(models.Model):
    # class Meta:
    #     verbose_name_plural = ""
    #     verbose_name = ""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, blank=True)

    def __str__(self):
        return self.user.email


def post_save_user_receiver(sender, instance, created, **kwargs):
    if created:
        library = UserLibrary.objects.create(user=instance)

        purchased_products = PurchasedProduct.objects.filter(email=instance.email)
        for purchased_product in purchased_products:
            library.products.add(purchased_product.product)

        account = stripe.Account.create(
            type="express",
        )
        instance.stripe_account_id = account["id"]
        instance.save()


post_save.connect(post_save_user_receiver, sender=User)
