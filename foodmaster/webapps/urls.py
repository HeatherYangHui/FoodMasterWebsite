"""
URL configuration for webapps project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.urls import path, include
from foodmaster import views

app_name = "foodmaster"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home_view, name='home'),
    
    # Include django-allauth for Google OAuth 
    path('accounts/', include('allauth.urls')),  # allauth endpoints

    # Include your custom app’s URLs
    # path('', include('foodmaster.urls')),


    # URLS related to authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('password_reset/', views.password_reset_view, name='password_reset'),
    path('password_reset_confirm/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),

    # A custom route that redirects to the allauth Google login
    path('google_login/', views.google_login_redirect, name='google_login'),

    path('dashboard/', views.dashboard_view, name='dashboard'),

    path('restaurant_search/', views.restaurant_search_view, name='restaurant_search'),
]
