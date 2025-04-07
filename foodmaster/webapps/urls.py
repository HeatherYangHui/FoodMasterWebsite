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
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include




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

    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('social/', views.social_feed_view, name='social_feed'),
    path('create_post/', views.create_post_view, name='create_post'),
    path('ajax/like/<int:post_id>/', views.like_post_ajax, name='like_post_ajax'),
    path('ajax/comment/<int:post_id>/', views.add_comment_ajax, name='add_comment_ajax'),
    path('posts/<int:post_id>/delete/', views.delete_post_ajax, name='delete_post'),
    path('ajax/follow/<int:profile_id>/', views.toggle_follow, name='toggle_follow'),
    # restaurant details view
    path('restaurant/<str:place_id>/', views.restaurant_detail_view, name='restaurant_detail'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
