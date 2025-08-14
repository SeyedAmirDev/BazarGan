from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .cart import Cart


@receiver(user_logged_in)
def post_login(sender, user, request, **kwargs):
    cart = Cart(request)
    cart.sync_cart_items_from_db(user)
    print(f'user {user} logged in')

@receiver(user_logged_out)
def post_logout(sender, user, request, **kwargs):
    cart = Cart(request)
    cart.merge_cart_into_db(user)
    print(f'user {user} logged out')
