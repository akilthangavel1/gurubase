from django.contrib import admin
from .models import TickerBase, AccessToken
# Register your models here.
admin.site.register(TickerBase)
admin.site.register(AccessToken)