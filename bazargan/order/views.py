from django.views.generic import (
    TemplateView,
    FormView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.shortcuts import redirect

from decimal import Decimal

from .permissions import HasCustomerAccessPermission
from .models import UserAddress
from .forms import CheckoutForm
from .models import Order, OrderItem, Coupon

from cart.models import Cart as CartModel, CartItem as CartItemModel
from cart.cart import Cart as CartService


class OrderCheckoutView(LoginRequiredMixin, HasCustomerAccessPermission, FormView):
    template_name = "order/checkout.html"
    form_class = CheckoutForm
    success_url = reverse_lazy('order:completed')

    def get_form_kwargs(self):
        kwargs = super(OrderCheckoutView, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        cleaned_data = form.cleaned_data
        address = cleaned_data['address_id']
        coupon = cleaned_data['coupon']

        cart = CartModel.objects.get(user=user)
        order = self.create_order(user, address)

        self.create_order_items(order, cart)
        self.clear_cart(cart)

        total_price = order.calculate_total_price()
        self.apply_coupon(coupon, order, user, total_price)
        self.calculate_tax(order)

        order.save()

        return super().form_valid(form)


    def create_order(self, user, address):
        order = Order.objects.create(
            user=user,
            address=address.address,
            state=address.state,
            city=address.city,
            zip_code=address.zip_code,
        )
        return order

    def create_order_items(self, order, cart):
        cart_items = cart.cart_items.select_related("product")

        order_items = []

        for item in cart_items:
            order_item = OrderItem(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.get_price(),
            )
            order_items.append(order_item)

        OrderItem.objects.bulk_create(order_items)

    def clear_cart(self, cart):
        cart.cart_items.all().delete()
        CartService(self.request).clear()

    def apply_coupon(self, coupon, order, user, total_price):
        if coupon:
            total_price = total_price - round((total_price * Decimal(coupon.discount_percent/100)))
            order.coupon = coupon
            coupon.used_by.add(user)
            coupon.save()

        order.total_price = total_price

    # todo: add also calculate shipping based on state and city

    def calculate_tax(self, order):
        total_price = order.total_price
        total_tax = round((total_price * 9) / 100)
        order.total_price = total_price + total_tax

    def form_invalid(self, form):
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = CartModel.objects.get(user=self.request.user)
        context['addresses'] = UserAddress.objects.filter(user=self.request.user)
        total_price = cart.calculate_total_price()
        total_tax = round((total_price * 9) / 100)
        context['total_price'] = total_price + total_tax
        context['total_tax'] = total_tax
        return context


class OrderCompletedView(LoginRequiredMixin, HasCustomerAccessPermission, TemplateView):
    template_name = "order/completed.html"


class OrderFailedView(LoginRequiredMixin, HasCustomerAccessPermission, TemplateView):
    template_name = "order/failed.html"


class ValidateCouponView(LoginRequiredMixin, HasCustomerAccessPermission, View):

    def post(self, request, *args, **kwargs):
        code = request.POST.get('code')
        user = request.user

        status_code = 200
        message = "کد تخفیف با موفقیت اعمال شد."

        total_price = 0
        total_tax = 0

        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            return JsonResponse({'message': 'کد تخفیف یافت نشد.'}, status=404)
        else:
            if coupon.used_by.count() >= coupon.max_limit_usage:
                status_code, message = 403, 'ممحدودیت در تعداد استفاده.'

            elif coupon.expiration_date and coupon.expiration_date < timezone.now():
                status_code, message = 403, 'کد تخفیف منقضی شده است.'

            elif user in coupon.used_by.all():
                status_code, message = 403, 'این کد تخفیف قبلا توسط شما استفاده شده است.'

            else:
                cart = CartModel.objects.get(user=self.request.user)
                total_price = cart.calculate_total_price()
                if coupon.discount_percent:
                    total_price = total_price - round((total_price * Decimal(coupon.discount_percent / 100)))

                total_tax = round((total_price * 9) / 100)
                total_price = total_price + total_tax

        return JsonResponse({
            'message': message,
            'total_price': total_price,
            'total_tax': total_tax
        }, status=status_code)
