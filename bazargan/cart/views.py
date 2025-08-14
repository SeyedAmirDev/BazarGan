from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from django.views.generic.base import TemplateView
from django.shortcuts import get_object_or_404

from shop.models import Product, ProductStatusType

from .cart import Cart


class SessionAddProductView(View):
    def post(self, request, *args, **kwargs):
        product_id = request.POST.get('product_id')
        cart = Cart(request)

        product = get_object_or_404(Product, pk=product_id, status=ProductStatusType.publish.value)

        cart.add(product)

        if self.request.user.is_authenticated:
            cart.merge_cart_into_db(user=request.user)

        return JsonResponse({'cart': cart.get_cart_dict(), 'total_quantity': len(cart)})


class SessionUpdateProductQuantityView(View):
    def post(self, request, *args, **kwargs):
        cart = Cart(request)
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity'))

        if product_id and quantity:
            product = get_object_or_404(Product, pk=product_id, status=ProductStatusType.publish.value,
                                        stock__gte=quantity)
            cart.add(product, quantity, update_quantity=True)

            if self.request.user.is_authenticated:
                cart.merge_cart_into_db(user=request.user)

        return JsonResponse({'cart': cart.get_cart_dict(), 'total_quantity': len(cart)})


class SessionRemoveProductView(View):
    def post(self, request, *args, **kwargs):
        product_id = request.POST.get('product_id')
        cart = Cart(request)

        product = get_object_or_404(Product, pk=product_id, status=ProductStatusType.publish.value)

        cart.remove(product)

        if self.request.user.is_authenticated:
            cart.merge_cart_into_db(user=request.user)

        return JsonResponse({'cart': cart.get_cart_dict(), 'total_quantity': len(cart)})


class CartSummaryView(TemplateView):
    template_name = 'cart/cart-summary.html'
