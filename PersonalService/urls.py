# PersonalService/urls.py
#
# This file is the main URL configuration for the project. It defines the URL patterns for the project
# and maps them to the corresponding views.
"""
URL configuration for PersonalService project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path
from home import views as home_views

urlpatterns = [
    path('', home_views.home, name='home'),
    path('robot/feishu', home_views.feishu, name='robot_feishu'),
    path('admin/', admin.site.urls),
]
