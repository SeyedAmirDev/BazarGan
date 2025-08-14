from decimal import Decimal

from django.conf import settings

from shop.models import Product, ProductStatusType

from .models import Cart as CartModel, CartItem as CartItemModel

# TODO: Handle disabled/unpublished products in the cart gracefully:
#       1. Should we display a "Product disabled" message in the template,
#          or silently remove it from the cart? Avoid confusing the user.
#       2. Consider storing cart session data in Redis for better performance.

class Cart:
    def __init__(self, request):
        """
        Initialize the cart.
        """
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # save an empty cart in the session
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, update_quantity=False):
        """
        Add a product to the cart or update its quantity.
        """
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0}
        if update_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        self.save()

    def save(self):
        # update the session cart
        self.session[settings.CART_SESSION_ID] = self.cart
        # mark the session as "modified" to make sure it is saved
        self.session.modified = True

    def remove(self, product):
        """
        Remove a product from the cart.
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        """
        Iterate over the items in the cart and get the products
        from the database.
        """
        product_ids = self.cart.keys()
        # get the product objects and add them to the cart
        # TODO: I added a product to my cart, but after 5 minutes the product was disabled (unpublished).
        #   However, it still exists in my cart!
        #     When I filter results with `status=ProductStatusType.PUBLISH.value`,
        #       the cart item's product object is missing (not included).
        products = Product.objects.filter(id__in=product_ids, status=ProductStatusType.publish.value)
        for product in products:
            self.cart[str(product.id)]['product'] = product
            self.cart[str(product.id)]['price'] = str(product.get_price())

        for item in self.cart.values():
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        """
        Count all items in the cart.
        """
        return sum(item['quantity'] for item in self.cart.values())
    # todo: calculate tax
    def get_total_price(self):
        """
        Return the total price of the cart.
        """
        # TODO: I added a product to my cart, but after 5 minutes the product was disabled (unpublished).
        #   However, it still exists in my cart!
        #     When I filter results with `status=ProductStatusType.PUBLISH.value`,
        #       the cart item's product object is missing (not included).
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids).only('id', 'price')
        total = Decimal(0)

        for product in products:
            product_id = str(product.id)
            if product_id in product_ids:
                quantity = self.cart[product_id]['quantity']
                total += Decimal(product.get_price()) * quantity

        return total

    def get_cart_dict(self):
        """
        Return the cart as a dictionary.
        """
        return self.cart

    def clear(self):
        # remove cart from session
        del self.session[settings.CART_SESSION_ID]
        self.session.modified = True

    def sync_cart_items_from_db(self, user):
        """
        Sync the session cart with the cart items stored in the database for the given user.
        """
        cart, _ = CartModel.objects.get_or_create(user=user)
        cart_items = CartItemModel.objects.filter(cart=cart)

        for cart_item in cart_items:
            product_id = str(cart_item.product.pk)
            if product_id in self.cart:
                cart_item.quantity = self.cart[product_id]['quantity']
            else:
                new_item = {
                    'quantity': cart_item.quantity,
                }
                self.cart[product_id] = new_item
        self.merge_cart_into_db(user, cart)
        self.save()

    def merge_cart_into_db(self, user, cart=None):
        """
        Persist the session cart into the database for the specified user.
        """
        if not cart:
            cart, _ = CartModel.objects.get_or_create(user=user)

        product_ids = self.cart.keys()
        products_qs = Product.objects.filter(id__in=product_ids)
        products = {str(p.id): p for p in products_qs}

        for key, item in self.cart.items():
            product = products.get(key)
            # TODO: Replace per-item get_or_create with a bulk approach:
            #  1. Fetch all existing cart items for the given cart + product IDs in one query.
            #  2. Create a dict mapping product_id -> CartItem for quick lookup.
            #  3. Collect new items in a list and insert them with bulk_create().
            #  4. Collect updated items in a list and update them with bulk_update().

            # todo: add condition that check if product disabled remove them
            cart_item, _ = CartItemModel.objects.get_or_create(product=product, cart=cart)
            cart_item.quantity = item['quantity']
            cart_item.save()

        CartItemModel.objects.filter(cart=cart).exclude(product__id__in=product_ids).delete()
