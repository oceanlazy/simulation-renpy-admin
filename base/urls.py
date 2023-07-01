from django.contrib import admin
from django.views.generic.base import RedirectView
from django.urls import path

urlpatterns = [path('', RedirectView.as_view(url='/admin/')), path('admin/', admin.site.urls)]
