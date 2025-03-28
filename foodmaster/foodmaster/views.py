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
from .models import Post
from .models import Profile

from django.views.decorators.http import require_POST
from .models import Comment


from django.shortcuts import get_object_or_404, redirect

import math
import requests
from django.conf import settings
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys

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
def get_nearby_restaurants(lat, lng, radius=500, cuisine=None):
    endpoint = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,places.location,"
            "places.types,places.rating,places.photos,places.priceLevel,"
            "places.userRatingCount"
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
    print(payload)

    response = requests.post(endpoint, headers=headers, json=payload)
    data = response.json()
    restaurants = []
    if "places" in data:
        for place in data["places"]:
            display_name = place.get("displayName")
            print(display_name)
            rating = place.get("rating", "N/A")
            address = place.get("formattedAddress", "No address provided")
            photo_url = None
            price_level = place.get("priceLevel")
            user_rating_count = place.get("userRatingCount")
            types = place.get("types", [])

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
                "name": {"text": display_name},
                "rating": rating,
                "address": address,
                "photo_url": photo_url,
                "priceLevel": price_level,
                "userRatingCount": user_rating_count,
                "types": types,
            })
            print(price_level)
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


# -----------------------------
# Social Feed View
# -----------------------------
def social_feed_view(request):
    posts = Post.objects.all().order_by('-created_at')
    return render(request, 'foodmaster/social_feed.html', {'posts': posts})



@login_required
def create_post_view(request):
    if request.method == 'POST':
        content = request.POST.get('content')
        category = request.POST.get('category', '')
        tags = request.POST.get('tags', '')
        photo = request.FILES.get('photo')
        if photo:
            try:
                image = Image.open(photo)
                image.thumbnail((1024, 1024))

                image_io = BytesIO()
                image_format = image.format if image.format else 'JPEG'
                image.save(image_io, format=image_format)
                # compress img when uploading to cut down latency
                # Create new InMemoryUploadedFile
                photo = InMemoryUploadedFile(
                    image_io,       # file
                    'photo',        # field name
                    photo.name,     # file name
                    f'image/{image_format.lower()}',  # content_type
                    image_io.tell(),# size
                    None            # charset
                )
            except Exception as e:
                print("Image processing error:", e)
        if tags:
            tags_list = [tag.strip() for tag in tags.split(',')]
        else:
            tags_list = []
        # Create a new Post instance
        Post.objects.create(
            author=request.user,
            content=content,
            category=category,
            tags=tags_list,
            photo=photo
        )
        return redirect('social_feed')
    return render(request, 'foodmaster/create_post.html')



@login_required
def add_comment_ajax(request, post_id):
    """
    AJAX endpoint for adding a comment to a post.
    Returns JSON with the newly created comment or an error.
    """
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        content = request.POST.get('content')  # 或者 JSON 方式获取
        if content:
            new_comment = Comment.objects.create(
                post=post,
                author=request.user,
                content=content
            )
            return JsonResponse({
                'success': True,
                'comment_id': new_comment.id,
                'author': new_comment.author.username,
                'content': new_comment.content,
                'created_at': new_comment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'comments_count': post.comments.count()
            })
        else:
            return JsonResponse({'success': False, 'error': 'Empty content'}, status=400)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


from django.http import JsonResponse

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