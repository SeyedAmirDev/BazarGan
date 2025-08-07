from django.urls import path, re_path

from . import views

app_name = 'shop'

urlpatterns = [
    path('product/grid/', views.ProductGridView.as_view(), name='product-grid'),
    re_path(r'product/(?P<slug>[-\w]+)/detail/', views.ProductDetailView.as_view(), name='product-detail'),
    path('add-or-remove-wishlist/', views.AddOrRemoveWishlistView.as_view(), name='add-or-remove-wishlist'),
]