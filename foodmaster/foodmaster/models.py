from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

# Create your models here. 
# test push


class SavedRestaurant(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_restaurants')
    place_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'place_id')

    def __str__(self):
        return f"{self.user.username} saved {self.name}"
class Restaurant(models.Model):
    place_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    cuisine = models.CharField(max_length=255)
    price_range = models.CharField(max_length=10)
    rating = models.FloatField()
    reviews = models.IntegerField()
    # Store latitude and longitude as decimal numbers
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    status = models.CharField(max_length=255, blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.name

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    followers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='following_profiles', blank=True)
    following = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='followers_profiles',
        blank=True
    )
    
    def __str__(self):
        return self.user.username


class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    category = models.CharField(max_length=50, blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    photo = models.ImageField(upload_to='post_photos/', blank=True, null=True)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_posts', blank=True)
    shared_from = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='shares')
    shared_restaurant_place_id = models.CharField(max_length=255, blank=True, null=True)
    shared_restaurant_name = models.CharField(max_length=255, blank=True, null=True)
    # shared_restaurant_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    # shared_restaurant_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    shared_restaurant_city = models.CharField(max_length=255, blank=True, null=True)
    def total_likes(self):
        return self.likes.count()
    
    def __str__(self):
        return f'{self.author.username} - {self.created_at}'


class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='postimage_set')
    image = models.ImageField(upload_to='post_photos/')
    
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.id}"
    


class SavedRecipe(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_recipes')
    recipe_id = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'recipe_id')

    def __str__(self):
        return f"{self.user.username} saved {self.title}"