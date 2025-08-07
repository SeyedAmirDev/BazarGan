from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _


User = get_user_model()


class ProductStatusType(models.IntegerChoices):
    publish = 1, _('display')
    draft = 2, _('no_display')


class ProductCategory(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Product Categories'
        ordering = ['-created_date']

    def __str__(self):
        return self.title



class Product(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='products')
    category = models.ManyToManyField(ProductCategory)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    image = models.ImageField(default='default/product-image.png', upload_to='product/img')
    description = models.TextField()
    brief_description = models.TextField(null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    status = models.IntegerField(choices=ProductStatusType.choices, default=ProductStatusType.draft.value)
    price = models.DecimalField(default=0, max_digits=10, decimal_places=0)
    discount_percent = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']

    def __str__(self):
        return self.title

    def get_price(self):
        discount_amount = self.price * Decimal(self.discount_percent / 100)
        discounted_amount = self.price - discount_amount
        return round(discounted_amount)

    def get_show_price(self):
        price = self.get_price()
        return '{:,}'.format(price)

    def is_discounted(self):
        return self.discount_percent != 0

    def get_show_raw_price(self):
        return '{:,}'.format(self.price)

    def is_published(self):
        return self.status == ProductStatusType.publish.value


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    file = models.ImageField(upload_to='product/extra-img')

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)


class WishlistProduct(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='wishlists')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlists')

    def __str__(self):
        return self.product.title
