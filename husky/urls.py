"""husky URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from system.views import index
from django.contrib import admin
from django.urls import path
from rest_framework.authtoken import views
from rest_framework.documentation import include_docs_urls
from django.conf.urls import include


API_TITLE = '文档'
API_DESCRIPTION = '文档'


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index),
    path('index', index, name="index"),
    path('system/', include('system.urls', namespace='system')),
    path('asset/', include('asset.urls', namespace='asset')),
    path('router/', include('router.urls', namespace='router')),
    path('token', views.obtain_auth_token),
    path('docs', include_docs_urls(title=API_TITLE, description=API_DESCRIPTION, authentication_classes=[],
                                   permission_classes=[])),
]



