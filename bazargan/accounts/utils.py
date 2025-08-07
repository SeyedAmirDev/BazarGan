import threading

from django.conf import settings
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode


class EmailThread(threading.Thread):
    def __init__(self, email_obj, to):
        threading.Thread.__init__(self)
        self.email_obj = email_obj
        self.to = to

    def run(self):
        self.email_obj.send(to=self.to)


def encode_uid(pk):
    return force_str(urlsafe_base64_encode(force_bytes(pk)))


def decode_uid(pk):
    return force_str(urlsafe_base64_decode(pk))

def activation_token_expiry_hours():
    return getattr(settings, "ACTIVATION_ACCOUNT_TIMEOUT", 24 * 60 * 60) // 60 * 60

def reset_token_expiry_hours():
    return getattr(settings, "RESET_ACCOUNT_TIMEOUT", 24 * 60 * 60) // 60 * 60
