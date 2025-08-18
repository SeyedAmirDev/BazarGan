from django.utils import timezone
from django import forms

from .models import UserAddress, Coupon


class CheckoutForm(forms.Form):
    address_id = forms.IntegerField(required=True)
    coupon = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(CheckoutForm, self).__init__(*args, **kwargs)

    def clean_address_id(self):
        address_id = self.cleaned_data['address_id']

        user = self.request.user
        try:
            address = UserAddress.objects.get(pk=address_id, user=user)
        except UserAddress.DoesNotExist:
            raise forms.ValidationError('Address does not exist.')

        return address


    def clean_coupon(self):
        code = self.cleaned_data['coupon']

        if not code:
            return

        user = self.request.user
        coupon = None
        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            raise forms.ValidationError('کد تخفیف اشتباه است.')

        if coupon:
            if coupon.used_by.count() >= coupon.max_limit_usage:
                raise forms.ValidationError('محدودیت در تعداد استفاده.')

            if coupon.expiration_date and coupon.expiration_date < timezone.now():
                raise forms.ValidationError('کد تخفیف منقضی شده است.')

            if user in coupon.used_by.all():
                raise forms.ValidationError('این کد تخفیف قبلا توسط شما استفاده شده است.')

        return coupon
