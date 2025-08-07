from django.contrib import admin

from .models import Product, ProductImage, ProductCategory, WishlistProduct

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'stock', 'status', 'price', 'discount_percent', 'created_date')

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'parent', 'created_date')

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'created_date')

@admin.register(WishlistProduct)
class WishlistProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product')
