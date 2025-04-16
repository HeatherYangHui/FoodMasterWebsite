from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.contrib.auth.forms import PasswordChangeForm
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth import update_session_auth_hash

# For password reset functionality:
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth import logout
from django.db.models import Count
from django.core.files.base import ContentFile
from collections import Counter
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required


from .models import Post
from .models import Profile
from .models import PostImage
from .models import SavedRestaurant
from .models import SavedRecipe


from django.views.decorators.http import require_POST
from .models import Comment
from datetime import datetime, timezone
import pytz
from django.urls import reverse

import math
import requests
from django.conf import settings
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from urllib.parse import unquote
import ast



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
            messages.error(request, "Invalid username or password. Please try again.")
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

        # Automatically create a Profile tied to this new user
        Profile.objects.create(
            user=user,
            full_name=full_name  # Optionally set other fields
        )

        # Log the user in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('dashboard')
    else:
        return render(request, 'foodmaster/register.html')
    

@login_required
@require_POST
def toggle_save_restaurant_view(request):
    """
    Toggle saved restaurant for the current user.
    Expect POST parameters: place_id, name, address.
    If a SavedRestaurant record exists for this user and place_id, delete it (unsaved);
    otherwise, create it (saved).
    Return JSON with new state.
    """
    place_id = request.POST.get('place_id')
    name = request.POST.get('name')
    address = request.POST.get('address', '')
    photo_link = request.POST.get('photo_urls', '')
    if not place_id or not name:
        return JsonResponse({'success': False, 'error': 'Missing restaurant information.'}, status=400)
    
    try:
        # If already saved, remove it.
        saved = SavedRestaurant.objects.get(user=request.user, place_id=place_id)
        saved.delete()
        new_state = 'unsaved'
    except SavedRestaurant.DoesNotExist:
        # Otherwise, create new record.

        SavedRestaurant.objects.create(
        user=request.user,
        place_id=place_id,
        name=name,
        address=address,
        photo_url=photo_link
        )
        new_state = 'saved'
    
    return JsonResponse({'success': True, 'state': new_state})

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
        user = request.user
        new_full_name = request.POST.get('full_name', user.first_name)
        new_username = request.POST.get('username', user.username)
        new_bio = request.POST.get('bio', user.profile.bio)
        new_food_preferences = request.POST.get('food_preferences', '') 

        user.first_name = new_full_name
        user.username = new_username
        user.save()

        profile = user.profile
        profile.bio = new_bio
        if new_food_preferences:
            food_preferences_list = [pref.strip() for pref in new_food_preferences.split(',') if pref.strip()]
            profile.food_preferences = food_preferences_list
        else:
            profile.food_preferences = []
        profile_image = request.FILES.get('profile_image')
        if profile_image:
            try:
                image = Image.open(profile_image)
                image.thumbnail((300, 300))  

                image_io = BytesIO()
                image_format = image.format if image.format else 'JPEG'
                image.save(image_io, format=image_format)

                
                profile.profile_image = InMemoryUploadedFile(
                    image_io,      
                    'ImageField', 
                    profile_image.name,  
                    f'image/{image_format.lower()}',  # content_type
                    image_io.tell(), 
                    None            # charset
                )
            except Exception as e:
                print("Profile image processing error:", e)
        profile.save()

        messages.success(request, "Profile updated successfully.")
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
# Delete Account View
# -----------------------------
@login_required
def delete_account_view(request):
    if request.method == "POST":
        # Store user in a variable before logout
        current_user = request.user

        # Log the user out first, so session is cleared
        logout(request)

        # Now delete the user object, which should also delete the Profile
        # if your Profile has on_delete=models.CASCADE
        current_user.delete()

        messages.success(request, "Your account has been deleted successfully.")
        return redirect('home')  # or wherever you want them to go
    else:
        # If it's not a POST, just redirect or do something else.
        return redirect('profile')


# -----------------------------
# Password Reset View (by email verification)
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
# Reset Password View (by re-enter old password)
# -----------------------------
@login_required
def reset_password_view(request):
    """
    Allows a logged-in user to reset their password by entering their old password
    and a new password (with confirmation). If the old password is correct, updates the password.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Update the session hash so the user isn't logged out
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been changed successfully.")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'foodmaster/reset_password.html', {'form': form})


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
def get_nearby_restaurants(lat, lng, radius=500, cuisine=None):
    endpoint = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,places.location,"
            "places.rating,places.photos,places.priceLevel,"
            "places.userRatingCount,places.primaryTypeDisplayName"
        )
    }
    
    # Define a mapping from filter input to Places API type
    cuisine_map = {
        "italian": "italian_restaurant",
        "chinese": "chinese_restaurant",
        "american": "american_restaurant",
        "japanese": "japanese_restaurant",
        "mexican": "mexican_restaurant",
    }
    
    # Set the includedTypes based on the cuisine filter.
    if cuisine:
        cuisine_key = cuisine.lower()
        included_types = [cuisine_map[cuisine_key]] if cuisine_key in cuisine_map else ["restaurant"]
    else:
        included_types = ["restaurant"]
    
    payload = {
        #"includedPrimaryTypes": ["restaurant"],
        "includedTypes": included_types,
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
            price_level = place.get("priceLevel")
            user_rating_count = place.get("userRatingCount")
            # types = place.get("types", [])
            # primary_type = place.get("primaryType")
            primary_type_display_name = place.get("primaryTypeDisplayName", {}).get("text", "Unknown Cuisine")
            # Extrace unique place id, preparing for details search
            place_id = place.get("id")

            # Extract lat/lng from the "location" key
            location_data = place.get("location", {})
            place_lat = location_data.get("latitude")
            place_lng = location_data.get("longitude")

            photos_data = place.get("photos", [])
            if photos_data:
                first_photo = photos_data[0]
                photo_resource = first_photo.get("name")
                if photo_resource:
                    photo_url = (
                        f"https://places.googleapis.com/v1/{photo_resource}/media"
                        f"?maxHeightPx=400&maxWidthPx=400&key={settings.GOOGLE_PLACES_API_KEY}"
                    )

            restaurants.append({
                "id": place_id,  # <-- Added unique restaurant id
                "name": {"text": display_name},
                "rating": rating,
                "address": address,
                "photo_url": photo_url,
                "priceLevel": price_level,
                "userRatingCount": user_rating_count,
                # "types": types,
                "latitude": place_lat,
                "longitude": place_lng,
                # "primaryType": primary_type,
                "primaryTypeDisplayName": primary_type_display_name,
            })
            print(restaurants)
    else:
        print("No places found or error:", data.get("error", data))
    
    return restaurants


def restaurant_search_view(request):
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')

    # Get filter parameters
    cuisine = request.GET.get('cuisine', '')    # e.g. "italian"
    price = request.GET.get('price', '')        # e.g. "2"
    distance = request.GET.get('distance', '')  # e.g. "2" => 2 miles
    rating = request.GET.get('rating', '')      # e.g. "4.5"

    # Convert miles to meters (approx 1609.34 meters per mile)
    default_radius = 500  # fallback if distance is empty
    try:
        radius_meters = int(distance) * 1609 if distance else default_radius
    except ValueError:
        radius_meters = default_radius

    restaurants = [] 
    
    # Only call the API if lat/lng exist
    if lat and lng:
        try:
            user_lat = float(lat)
            user_lng = float(lng)
            # Pass radius and cuisine to the function
            restaurants = get_nearby_restaurants(
                user_lat,
                user_lng,
                radius=radius_meters,
                cuisine=cuisine,
            )
        except ValueError:
            print("Error: Latitude or longitude could not be converted to float.")
    else:
        print("No latitude/longitude found in query parameters.")
    
    # -------------------------------
    # Additional Python-side filtering
    # -------------------------------

    # 1) Filter by rating
    if rating:
        # Convert rating string (e.g. "4.5") to float
        try:
            min_rating = float(rating)
            filtered = []
            for r in restaurants:
                if r["rating"] != "N/A":
                    try:
                        if float(r["rating"]) >= min_rating:
                            filtered.append(r)
                    except ValueError:
                        pass
            restaurants = filtered
        except ValueError:
            pass  # ignore if rating can't convert

    # 2) Filter by price
    if price:
        if price == "1":
            filter_price_level = "PRICE_LEVEL_INEXPENSIVE"
        elif price == "2":
            filter_price_level = "PRICE_LEVEL_MODERATE"
        elif price == "3":
            filter_price_level = "PRICE_LEVEL_EXPENSIVE"
        else:
            filter_price_level = "PRICE_LEVEL_VERY_EXPENSIVE"
            
        try:
            price_level = filter_price_level
            restaurants = [
                r for r in restaurants
                if r.get("priceLevel") == price_level
            ]
        except ValueError:
            pass

    context = {
        'restaurants': restaurants,
        'google_api_key': settings.GOOGLE_PLACES_API_KEY,
        'lat': lat,
        'lng': lng,
    }
    return render(request, 'foodmaster/restaurant_search.html', context)


def parse_close_time(iso_string):
    """
    Given an ISO8601 string like '2025-04-08T01:00:00Z',
    parse it as UTC and convert to local time, returning a formatted string like '9:00 PM'.
    """
    dt_utc = datetime.strptime(iso_string, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    local_tz = pytz.timezone("America/New_York")  # Or your local time zone
    dt_local = dt_utc.astimezone(local_tz)
    return dt_local.strftime("%I:%M %p")  # e.g. "09:00 PM"


def restaurant_detail_view(request, place_id):
    endpoint = f"https://places.googleapis.com/v1/places/{place_id}"
    fields = (
        "id,displayName,formattedAddress,photos,types,"
        "rating,userRatingCount,priceLevel,currentOpeningHours,"
        "regularOpeningHours,editorialSummary,internationalPhoneNumber,"
        "websiteUri,primaryTypeDisplayName,location,reviews,"
        "delivery,dineIn,servesVegetarianFood,paymentOptions,parkingOptions"
    )
    url = f"{endpoint}?fields={fields}&key={settings.GOOGLE_PLACES_API_KEY}"
    
    resp = requests.get(url, headers={"Content-Type": "application/json"})
    if resp.status_code != 200:
        # Fallback if there's an error
        restaurant = {
            "id": place_id,
            "name": "Unknown Restaurant",
            "types": [],
            "rating": "N/A",
            "reviews": "N/A",
            "reviews_count": "N/A",
            "reviews_list": [],
            "price_range": "N/A",
            "description": "No description available.",
            "address": "N/A",
            "phone": "N/A",
            "website": "N/A",
            "primary_type": "Unknown Cuisine",
            # "photo_url": None,
            "photo_url": [],
            "hours": None,
            "closes_at": None,
            "latitude": 0,
            "longitude": 0,
        }
    else:
        data = resp.json()
        # print(data.get("delivery", "N/A"))
        # print(data.get("dineIn", "N/A"))
        # print(data.get("servesVegetarianFood", "N/A"))
        # print(data.get("paymentOptions", "N/A"))
        # print(data.get("parkingOptions", "N/A"))

        # Extract core fields
        display_name_obj = data.get("displayName", {})
        primary_type = data.get("primaryTypeDisplayName", {}).get("text", "Unknown Cuisine")
        restaurant_name = display_name_obj.get("text", "N/A")
        address = data.get("formattedAddress", "N/A")
        rating = data.get("rating", "N/A")
        user_rating_count = data.get("userRatingCount", "N/A")
        price_level = data.get("priceLevel", "N/A")
        editorial_summary = data.get("editorialSummary", {}).get("text", "No description available.")
        phone = data.get("internationalPhoneNumber", "N/A")
        website = data.get("websiteUri", "N/A")
        delivery = data.get("delivery", "N/A")
        dine_in = data.get("dineIn", "N/A")
        serves_vegetarian_food = data.get("servesVegetarianFood", "N/A")
        payment_options = data.get("paymentOptions", "N/A")
        parking_options = data.get("parkingOptions", "N/A")
        

        # Convert the priceLevel string to dollar signs
        price_map = {
            "PRICE_LEVEL_INEXPENSIVE": "$",
            "PRICE_LEVEL_MODERATE": "$$",
            "PRICE_LEVEL_EXPENSIVE": "$$$",
            "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$"
        }
        price_range = price_map.get(price_level, "N/A")

        # Photo
        photo_urls = []
        photos = data.get("photos", [])
        for photo_obj in photos[:3]:
            photo_resource = photo_obj.get("name")
            if photo_resource:
                url = (
                    f"https://places.googleapis.com/v1/{photo_resource}/media"
                    f"?maxHeightPx=400&maxWidthPx=400&key={settings.GOOGLE_PLACES_API_KEY}"
                )
                photo_urls.append(url)

        # Hours
        hours_data = data.get("currentOpeningHours") or data.get("regularOpeningHours")
        
        # If there's a nextCloseTime, parse it
        closes_at = None
        if hours_data and "nextCloseTime" in hours_data:
            iso_close = hours_data["nextCloseTime"]  # e.g. "2025-04-08T01:00:00Z"
            closes_at = parse_close_time(iso_close)

        # Extract restaurant location from the "location" field if available.
        location_data = data.get("location", {})
        restaurant_lat = location_data.get("latitude", 0)
        restaurant_lng = location_data.get("longitude", 0)

        # Extract reviews
        reviews_data = data.get("reviews", [])
        reviews_list = reviews_data[:5]  # Slice for up to 5 reviews

        restaurant = {
            "id": place_id,
            "name": restaurant_name,
            "primary_type": primary_type,  # Use primary type for display
            "rating": rating,
            "reviews": user_rating_count,
            "price_range": price_range,  # e.g. $$, $$$
            "description": editorial_summary,
            "address": address,
            "phone": phone,
            "website": website,
            "delivery": delivery,
            "dine_in": dine_in,
            "serves_vegetarian_food": serves_vegetarian_food,
            "payment_options": payment_options,
            "parking_options": parking_options,
            # "photo_url": photo_url,
            "photo_urls": photo_urls,
            "hours": hours_data,     # e.g. { openNow: True/False, weekdayDescriptions: [...], ... }
            "closes_at": closes_at,  # e.g. "9:00 PM"
            "reviews_list": reviews_list,
            "latitude": restaurant_lat,
            "longitude": restaurant_lng,
        }
        # print(restaurant)
    
    # context = {"restaurant": restaurant}
    user_lat = request.GET.get('lat', '0')
    user_lng = request.GET.get('lng', '0')

    is_saved = False
    if request.user.is_authenticated:
        is_saved = request.user.saved_restaurants.filter(place_id=restaurant['id']).exists()
    
    context = {
        "restaurant": restaurant,
        "lat": user_lat,
        "lng": user_lng,
        'google_api_key': settings.GOOGLE_PLACES_API_KEY,
        'is_saved': is_saved,
    }
    return render(request, 'foodmaster/restaurant_detail.html', context)


# -----------------------------
# Social Feed View
# -----------------------------
def social_feed_view(request):
    posts = Post.objects.all()
    filter_value = request.GET.get('filter', '')  

    if filter_value == 'following':
        posts = posts.filter(author__profile__followers=request.user)
    elif filter_value in ['breakfast', 'lunch', 'dinner', 'dessert']:
        posts = posts.filter(category__iexact=filter_value)
    elif filter_value == 'all':
        pass

    if filter_value == 'trending':
        posts = posts.annotate(num_likes=Count('likes')).order_by('-num_likes')
    else:
        posts = posts.order_by('-created_at')
        
    all_tags = []
    for post in posts:
        if post.tags:  
            all_tags.extend(post.tags)
    trending_tags = [tag for tag, count in Counter(all_tags).most_common(5)]
    
    suggested_users = []
    if request.user.is_authenticated:
        suggested_users = get_suggested_users(request.user)

    context = {
        'posts': posts,
        'suggested_users': suggested_users,
        'trending_tags': trending_tags,
    }
    
    return render(request, 'foodmaster/social_feed.html', context)


def get_suggested_users(user):
    """
    Recommend other users based on mutual follows.
    1. Retrieve the list of Profiles followed by the current user.
    2. Iterate through all other users' Profiles and calculate the size of the intersection between their follow lists and the current user's follow list.
    3. Sort the results in descending order based on the number of mutual follows. If there are any mutual follows, return the top 5; otherwise, return 5 random recommendations.
    4. Cache the result for 1 hour to reduce redundant computations.
    """
# Suggest users based on mutual followings:
# 1. Get the profiles the current user is following.
# 2. For all other users, calculate the number of shared followings with the current user.
# 3. Sort by the number of shared followings in descending order.
# 4. If fewer than 5 good matches, fill the rest randomly.
# 5. Cache the result for performance (1 hour).
    cache_key = f'suggested_users_{user.id}'
    suggested_profiles = cache.get(cache_key)
    if suggested_profiles is not None:
        return suggested_profiles

    # Get the set of profiles the current user follows.
    current_following = set(user.following_profiles.all())
    suggestions = []
    # For each other profile, calculate mutual follows.
    for profile in Profile.objects.exclude(user=user):
        candidate_following = set(profile.user.following_profiles.all())
        common_count = len(current_following.intersection(candidate_following))
        suggestions.append((profile, common_count))

    # Sort all candidate profiles by number of mutual followers.
    suggestions.sort(key=lambda item: item[1], reverse=True)

    suggested_profiles = [item[0] for item in suggestions if item[1] > 0][:5]

    # If fewer than 5 suggestions, fill with random profiles.
    if len(suggested_profiles) < 5:
        remaining = Profile.objects.exclude(user=user).exclude(
            id__in=[profile.id for profile in suggested_profiles]
        ).order_by('?')[:(5 - len(suggested_profiles))]
        suggested_profiles = list(suggested_profiles) + list(remaining)
    # Store the result in cache for 1 hour to improve performance.
    cache.set(cache_key, suggested_profiles, 3600)  
    return suggested_profiles


# Helper function: get the city
def get_city_from_coordinates(lat, lng):
    """
    Uses the Google Geocoding API to convert a given latitude/longitude
    into a human-readable city name.

    Optional URL parameters:
      - language: Set to 'en' for English results.

    Returns the city name if found; otherwise, "Unknown City".
    """
    api_key = settings.GOOGLE_PLACES_API_KEY 
    # Construct the URL with language parameter to enforce English results.
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={api_key}&language=en"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print("Geocoding API error:", response.status_code, response.text)
            return "Unknown City"
        data = response.json()
        if data.get("status") == "OK":
            # Loop through results to find an address component of type 'locality'
            for result in data.get("results", []):
                for component in result.get("address_components", []):
                    if "locality" in component.get("types", []):
                        return component.get("long_name")
            # Fallback: if no locality is found, try administrative_area_level_1
            for result in data.get("results", []):
                for component in result.get("address_components", []):
                    if "administrative_area_level_1" in component.get("types", []):
                        return component.get("long_name")
        else:
            print("Geocoding API returned non-OK status:", data.get("status"))
            return "Unknown City"
    except Exception as e:
        print("Exception during reverse geocoding:", e)
    return "Unknown City"


@login_required
@require_POST
def delete_comment_ajax(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user == comment.author or request.user == comment.post.author:
        post = comment.post
        comment.delete()
        updated_count = post.comments.count()
        return JsonResponse({
            'success': True,
            'comment_id': comment_id,
            'comments_count': updated_count
        })
    else:
        return JsonResponse({'success': False, 'error': 'No permission'}, status=403)
    
    
@login_required
def create_post_view(request):
    cuisine = request.GET.get('cuisine', '') or request.POST.get('cuisine', '')
    lat_str = request.POST.get('lat', '') or request.GET.get('lat', '0')
    lng_str = request.POST.get('lng', '') or request.GET.get('lng', '0')

    try:
        rest_lat = float(lat_str)
    except ValueError:
        rest_lat = 0.0
    try:
        rest_lng = float(lng_str)
    except ValueError:
        rest_lng = 0.0

    city = get_city_from_coordinates(rest_lat, rest_lng)
    if request.method == 'POST':
        content = request.GET.get('content') or request.POST.get('content', '')
        category = request.POST.get('category', '')
        tags = request.POST.get('tags', '')
        photos = request.FILES.getlist('photos')
        
        photo_files = []
        for photo in photos:
            try:
                image = Image.open(photo)
                image.thumbnail((1024, 1024))
 
                image_io = BytesIO()
                image_format = image.format if image.format else 'JPEG'
                image.save(image_io, format=image_format)
                processed_photo = InMemoryUploadedFile(
                    image_io, 'photo', photo.name, f'image/{image_format.lower()}', image_io.tell(), None
                )
                photo_files.append(processed_photo)
            except Exception as e:
                print("Image processing error:", e)
        if tags:
            tags_list = [tag.strip() for tag in tags.split(',')]
        else:
            tags_list = []
        # Create a new Post instance without a photo field
        place_id = request.POST.get('place_id', '') or request.GET.get('place_id', '')
        rest_name = request.POST.get('rest_name', '') or request.GET.get('rest_name', '')

        post = Post.objects.create(
            author=request.user,
            content=content,
            category=category,
            tags=tags_list,
            shared_restaurant_place_id=place_id,
            shared_restaurant_name=rest_name,
            shared_restaurant_city=city,
            shared_cuisine = cuisine
        )

        # Save multiple photos if any
        for processed_photo in photo_files:
            # Assuming a PostImage model exists with a ForeignKey to Post and an ImageField named 'image'
            PostImage.objects.create(post=post, image=processed_photo)
        return redirect('social_feed')
    
    context = {
        'cuisine': cuisine,
        'place_id': request.GET.get('place_id', ''),
        'rest_name': request.GET.get('rest_name', ''),
        'city': city,
    }
    print("DEBUG context in recipe_detail_view:",cuisine)
    return render(request, 'foodmaster/create_post.html', context)


@login_required
def add_comment_ajax(request, post_id):
    """
    AJAX endpoint for adding a comment to a post.
    Returns JSON with the newly created comment or an error.
    """
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        content = request.POST.get('content') 
        
        if content:
            new_comment = Comment.objects.create(
                post=post,
                author=request.user,
                content=content
            )
            can_delete = (request.user == new_comment.author or request.user == post.author)
            return JsonResponse({
                'success': True,
                'comment_id': new_comment.id,
                'author': new_comment.author.username,
                'content': new_comment.content,
                'created_at': new_comment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'comments_count': post.comments.count(),
                'can_delete': can_delete
            })
        else:
            return JsonResponse({'success': False, 'error': 'Empty content'}, status=400)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


@login_required
def like_post_ajax(request, post_id):
    """
    AJAX endpoint for toggling 'like' on a post.
    Returns JSON with updated like info.
    """
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        user = request.user
        
        liked = user in post.likes.all()
        if liked:
            post.likes.remove(user)
        else:
            post.likes.add(user)
        
        return JsonResponse({
            'success': True,
            'liked': not liked, 
            'likes_count': post.likes.count()
        })
    else:
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


@login_required
def delete_post_ajax(request, post_id):
    """
    AJAX endpoint for deleting a post.
    Returns JSON with success status.
    """
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        if post.author == request.user:
            post.delete()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'You do not have permission to delete this post.'}, status=403)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


@login_required
def toggle_follow(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)
    current_user = request.user

    if profile.user == current_user:
        return JsonResponse({'success': False, 'error': "You cannot follow yourself."}, status=400)

    if current_user in profile.followers.all():
        profile.followers.remove(current_user)
        is_following = False
    else:
        profile.followers.add(current_user)
        is_following = True

    return JsonResponse({
        'success': True,
        'is_following': is_following,
        'followers_count': profile.followers.count()
    })
    
@login_required
def share_post_view(request, post_id):

    original_post = get_object_or_404(Post, id=post_id)
    
    if request.method == 'POST':
        comment = request.POST.get('comment', '')
    
        new_post = Post.objects.create(
            author=request.user,
            content=comment,
            category=original_post.category,  
            tags=original_post.tags,        
            shared_from=original_post,     
        )

        if original_post.photo:
            new_post.photo = original_post.photo
        new_post.save()
        messages.success(request, "Post shared successfully!")
        return redirect('social_feed')
    else:
       
        context = {
            'original_post': original_post,
        }
        return render(request, 'foodmaster/share_post.html', context)
    
    
# -----------------------------
# Recipe Search View
# -----------------------------
def recipe_search_view(request):
    """
    Renders the recipe search page with an input form.
    If a dish parameter is provided, validates it and then redirects to the recipe_detail view.
    """
    dish = request.GET.get('dish', '').strip()
    # First, try getting location from GET parameters.
    user_lat = request.GET.get('lat')
    user_lng = request.GET.get('lng')
    
    # Optionally, try to retrieve from session (if you stored these in a prior view)
    if not user_lat or not user_lng:
        user_lat = request.session.get('lat', '')
        user_lng = request.session.get('lng', '')
    
    if dish:
        # Pass the dish as the recipe_name to satisfy the URL pattern.
        target = reverse('recipe_detail')
        # Redirect to the recipe_detail page with lat and lng as query parameters.
        return redirect(f"{target}?dish={dish}&lat={user_lat}&lng={user_lng}")
    else:
        return render(request, 'foodmaster/recipe_search.html')



# -----------------------------
# Recipe Detail View
# -----------------------------
def get_nearby_markets(lat, lng, radius=1000, store_type='supermarket'):
    """
    Searches for nearby markets (e.g. supermarkets or grocery stores) 
    around the given lat/lng. We use an includedTypes list for "market" and "food_store".
    Returns up to 3 markets.
    """
    endpoint = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,places.location,"
            "places.primaryTypeDisplayName,places.rating,places.photos"
        )
    }
    
    # Adjust the types as needed. Here we request both “market” and “food_store”
    store_map = {
        'asian_store': 'asian_grocery_store',
        'food_store': 'food_store',
        'grocery_store': 'grocery_store',
        'supermarket': 'supermarket'  # default
    }
    
    # Resolve user selection to a valid type for the API
    included_type = store_map.get(store_type, 'supermarket')
    
    payload = {
        "includedTypes": included_type,
        "maxResultCount": 3,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lng
                },
                "radius": float(radius)
            }
        }
    }
    
    response = requests.post(endpoint, headers=headers, json=payload)
    markets = []
    try:
        data = response.json()
    except Exception as e:
        print("Error parsing response JSON:", e)
        data = {}

    if "places" in data:
        for place in data["places"]:
            display_name = place.get("displayName")
            rating = place.get("rating", "N/A")
            address = place.get("formattedAddress", "No address provided")
            photo_url = None
            # types = place.get("types", [])
            primary_type_display_name = place.get("primaryTypeDisplayName", {}).get("text", "Unknown Type")
            place_id = place.get("id")
            
            location_data = place.get("location", {})
            market_lat = location_data.get("latitude")
            market_lng = location_data.get("longitude")
            
            photos_data = place.get("photos", [])
            if photos_data:
                first_photo = photos_data[0]
                photo_resource = first_photo.get("name")
                if photo_resource:
                    photo_url = (
                        f"https://places.googleapis.com/v1/{photo_resource}/media"
                        f"?maxHeightPx=400&maxWidthPx=400&key={settings.GOOGLE_PLACES_API_KEY}"
                    )
            
            # Optionally calculate distance (if needed)
            distance = haversine_distance(lat, lng, market_lat, market_lng)
            
            markets.append({
                "id": place_id,
                "name": {"text": display_name},
                "rating": rating,
                "address": address,
                "photo_url": photo_url,
                # "types": types,
                "primaryTypeDisplayName": primary_type_display_name,
                "latitude": market_lat,
                "longitude": market_lng,
                "distance": f"{distance:.1f} miles"  # formatted distance
            })
    else:
        print("No markets found or error:", data.get("error", data))
    
    return markets


def recipe_detail_view(request):
    """
    Combined view that retrieves recipe information based on the 'dish' parameter via the Spoonacular API.
    If the API call fails, a placeholder recipe is used.
    Additionally, the user's location (lat/lng) and a store_type filter (defaulting to 'supermarket')
    are used to fetch nearby market data.
    """
    dish = request.GET.get('dish', '').strip()
    if not dish:
        messages.error(request, "No dish provided.")
        return redirect('recipe_search')
    
    # Retrieve the user's location from URL; default to 0 if not provided.
    user_lat = request.GET.get('lat', '0')
    user_lng = request.GET.get('lng', '0')
    try:
        user_lat = float(user_lat)
        user_lng = float(user_lng)
    except ValueError:
        user_lat, user_lng = 0, 0

    # Get the store_type from URL (default is 'supermarket')
    store_type = request.GET.get('store_type', 'supermarket')
    
    # Attempt to retrieve recipe details from Spoonacular.
    api_key = getattr(settings, "SPOONACULAR_API_KEY", None)
    if not api_key:
        raise Exception("SPOONACULAR_API_KEY is not configured in your settings.")

    url = "https://api.spoonacular.com/recipes/complexSearch"
    
    # Added parameters for instructions and nutrition.
    params = {
        "query": dish,
        "addRecipeInformation": "true",
        "fillIngredients": "true",  # ensures get ingredient details
        "instructionsRequired": "true",     # ensures instructions information is available
        "addRecipeInstructions": "true",    # returns analyzed instructions details
        "addRecipeNutrition": "true",       # returns nutritional information
        "number": "1",
        "apiKey": api_key,
    }
    
    response = requests.get(url, params=params)
    recipe_data = None
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            recipe_data = results[0]
            # Use the API-supplied key for ingredients; fallback if necessary.
            ingredients = recipe_data.get("includeIngredients") \
                          or recipe_data.get("usedIngredients") \
                          or recipe_data.get("extendedIngredients")
            recipe_data["displayIngredients"] = ingredients
    else:
        print("Spoonacular API error:", response.status_code, response.text)
    
    # Fallback: placeholder recipe data if API returns nothing.
    if not recipe_data:
        recipe_data = {
            "title": dish,  # use 'title' key so it matches in the template
            "cuisines": [],
            "readyInMinutes": "N/A",
            "preparationMinutes": "N/A",
            "cookingMinutes": "N/A",
            "aggregateLikes": "N/A",
            "reviews": "N/A",
            "displayIngredients": [{"original": "N/A"}],
            "instructions": "N/A",
            "analyzedInstructions": [],
            "nutrition": {"nutrients": []},
            "image": "N/A",
        }

    # Retrieve nearby markets using the user's coordinates and selected store_type.
    markets = get_nearby_markets(user_lat, user_lng, radius=2000, store_type=store_type)
    
    is_recipe_saved = False
    if request.user.is_authenticated:
        is_recipe_saved = request.user.saved_recipes.filter(recipe_id=recipe_data.get('title', '')).exists()

    context = {
        "recipe": recipe_data,
        "lat": user_lat,
        "lng": user_lng,
        "markets": markets,
        "store_type": store_type,
        'is_recipe_saved': is_recipe_saved,
    }
    
    return render(request, "foodmaster/recipe_detail.html", context)


@login_required
@require_POST
def toggle_save_recipe_view(request):
    """
    Toggle saved recipe for the current user.
    Expect POST parameters: recipe_id, title.
    If a SavedRecipe record exists for this user and recipe_id, delete it (i.e. unsave);
    otherwise, create it (save).
    Returns a JSON response with the new state ('saved' or 'unsaved').
    """
    recipe_title = request.POST.get('title')
    if not recipe_title:
        return JsonResponse({'success': False, 'error': 'Missing recipe title.'}, status=400)

    try:
        saved = SavedRecipe.objects.get(user=request.user, recipe_id=recipe_title)
        saved.delete()
        new_state = 'unsaved'
    except SavedRecipe.DoesNotExist:
        SavedRecipe.objects.create(user=request.user, recipe_id=recipe_title, title=recipe_title)
        new_state = 'saved'
    
    return JsonResponse({'success': True, 'state': new_state})

# -----------------------------
# Saved View
# -----------------------------

@login_required
def saved_view(request):
    saved_restaurants = SavedRestaurant.objects.filter(user=request.user).order_by('-saved_at')
    saved_recipes = SavedRecipe.objects.filter(user=request.user).order_by('-saved_at')
    context = {
        'saved_restaurants': saved_restaurants,
        'saved_recipes': saved_recipes,
    }
    return render(request, 'foodmaster/saved.html', context)