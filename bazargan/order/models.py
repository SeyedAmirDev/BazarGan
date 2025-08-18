from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

from decimal import Decimal


User = get_user_model()


class OrderStatusType(models.IntegerChoices):
    pending = 1, "در انتظار پرداخت"
    success = 2, "موفقیت آمیز"
    failed = 3, "لغو شده"


class UserAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')

    address = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    zip_code = models.CharField(max_length=255)

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.email} - {self.address}"


class Coupon(models.Model):
    code = models.CharField(max_length=100)
    discount_percent = models.IntegerField(default=0, validators = [MinValueValidator(0),MaxValueValidator(100)])
    max_limit_usage = models.PositiveIntegerField(default=10)
    used_by = models.ManyToManyField(User, related_name='coupon_users', blank=True, null=True)

    expiration_date = models.DateTimeField(null=True,blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.code}"


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')

    address = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    zip_code = models.CharField(max_length=255)

    total_price = models.DecimalField(default=0, decimal_places=0, max_digits=10)
    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, related_name='orders', blank=True, null=True)
    status = models.IntegerField(choices=OrderStatusType.choices, default=OrderStatusType.pending.value)

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_date"]

    def __str__(self):
        return f"{self.user.email} - {self.id}"

    def get_status(self):
        return {
            'id': self.status,
            'title': OrderStatusType(self.status).name,
            'label': OrderStatusType(self.status).label,
        }

    def get_full_address(self):
        return f'{self.state},{self.city},{self.address}'

    def calculate_total_price(self):
        return sum(item.price * item.quantity for item in self.order_items.all())

    @property
    def is_successful(self):
        return self.status == OrderStatusType.success.value

    def get_price(self):
        if self.coupon:
            return round(self.total_price - (self.total_price * Decimal(self.coupon.discount_percent / 100)))
        else:
            return self.total_price


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')

    product = models.ForeignKey('shop.Product', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=10)
    price = models.DecimalField(default=0,max_digits=10,decimal_places=0)

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.title} - {self.order.id}"
