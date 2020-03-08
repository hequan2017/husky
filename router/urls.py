from django.conf.urls import url
from django.urls import path
from router.views import *


app_name = "router"


urlpatterns = [
    path('login', user_login, name='login'),
    path('captcha/<int:image_uuid>)', user_captcha, name='captcha'),
    path('list_user_menu', ListUserMenu.as_view(), name='list_user_menu'),
    path('list_user_router', ListUserRouter.as_view(), name='list_user_router'),
]

