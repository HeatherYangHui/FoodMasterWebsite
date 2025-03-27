from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

# For password reset functionality:
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth import logout

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D  # Distance
from .models import Restaurant

import math
import requests
from django.conf import settings



# -----------------------------
# Login View
# -----------------------------
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        # Authenticate using email as username
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid credentials")
            return render(request, 'foodmaster/login.html')
    else:
        return render(request, 'foodmaster/login.html')


# -----------------------------
# Registration View
# -----------------------------
def register_view(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return render(request, 'foodmaster/register.html')

        # Create the user (using email as username)
        user = User.objects.create_user(username=email, email=email, password=password1)
        user.first_name = full_name
        user.save()

        # Log the user in and specify the backend
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('dashboard')
    else:
        return render(request, 'foodmaster/register.html')


# -----------------------------
# Google OAuth Redirect View
# -----------------------------
def google_login_redirect(request):
    # Redirect to django-allauth Google login URL
    return redirect('/accounts/google/login/')


# -----------------------------
# Dashboard View (Requires Login)
# -----------------------------
@login_required
def dashboard_view(request):
    return render(request, 'foodmaster/dashboard.html')


# -----------------------------
# Profile View (Requires Login)
# -----------------------------
@login_required
def profile_view(request):
    if request.method == 'POST':
        # For now, just update the built-in User fields
        user = request.user
        new_full_name = request.POST.get('full_name', user.first_name)
        new_username = request.POST.get('username', user.username)
        new_bio = request.POST.get('bio', '')  # Currently not stored anywhere, just a placeholder

        # Update built-in user fields
        user.first_name = new_full_name
        user.username = new_username
        user.save()

        messages.success(request, "Profile updated (placeholder logic).")
        return redirect('profile')

    return render(request, 'foodmaster/profile.html')


# -----------------------------
# Logout View
# -----------------------------
def logout_view(request):
    logout(request)
    return redirect('login')


# -----------------------------
# Profile View (Requires Login)
# -----------------------------
def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return redirect('login')


# -----------------------------
# Password Reset View
# -----------------------------
def password_reset_view(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(
                request=request,
                email_template_name='foodmaster/password_reset_email.html',
                subject_template_name='foodmaster/password_reset_subject.txt',
                use_https=request.is_secure(),
                token_generator=default_token_generator
            )
            messages.success(request, "Password reset link has been sent to your email.")
            return redirect('login')
        else:
            return render(request, 'foodmaster/password_reset.html', {'form': form})
    else:
        form = PasswordResetForm()
    return render(request, 'foodmaster/password_reset.html', {'form': form})


# -----------------------------
# Password Reset Confirm View
# -----------------------------
UserModel = get_user_model()

def password_reset_confirm_view(request, uidb64=None, token=None):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = UserModel._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        validlink = True
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Your password has been reset successfully.")
                return redirect('login')
        else:
            form = SetPasswordForm(user)
    else:
        validlink = False
        form = None

    return render(request, 'foodmaster/password_reset_confirm.html', {
        'form': form,
        'validlink': validlink
    })


# -----------------------------
# Restaurant Search View
# -----------------------------
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two lat/lng pairs in miles using the Haversine formula.
    """
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# helper function to get nearby restaurants
def get_nearby_restaurants(lat, lng, radius=500):
    endpoint = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
        # Request photo data by including places.photos in the field mask
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types,places.rating,places.photos"
    }
    payload = {
        "includedTypes": ["restaurant"],
        "maxResultCount": 10,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lng
                },
                "radius": float(radius)  # in meters
            }
        }
    }
    response = requests.post(endpoint, headers=headers, json=payload)
    data = response.json()
    restaurants = []
    if "places" in data:
        for place in data["places"]:
            display_name = place.get("displayName")
            rating = place.get("rating", "N/A")
            address = place.get("formattedAddress", "No address provided")
            photo_url = None
            photos_data = place.get("photos", [])
            if photos_data:
                first_photo = photos_data[0]
                # Use the new photo resource name from the "name" field
                photo_resource = first_photo.get("name")
                if photo_resource:
                    photo_url = (
                        f"https://places.googleapis.com/v1/{photo_resource}/media"
                        f"?maxHeightPx=400&maxWidthPx=400&key={settings.GOOGLE_PLACES_API_KEY}"
                    )
            restaurants.append({
                "name": {"text": display_name},
                "rating": rating,
                "address": address,
                "photo_url": photo_url,
            })
    else:
        print("No places found or error:", data.get("error", data))
    
    return restaurants



def restaurant_search_view(request):
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    restaurants = []
    
    if lat and lng:
        try:
            user_lat = float(lat)
            user_lng = float(lng)
            restaurants = get_nearby_restaurants(user_lat, user_lng)
        except ValueError:
            print("Error: Latitude or longitude could not be converted to float.")
    else:
        print("No latitude/longitude found in query parameters.")
    
    context = {
        'restaurants': restaurants,
        'google_api_key': settings.GOOGLE_PLACES_API_KEY,
    }
    
    return render(request, 'foodmaster/restaurant_search.html', context)



