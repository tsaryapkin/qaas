from django.urls import re_path
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()


urlpatterns = router.urls
