from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class User(AbstractUser):
    """Extended user model with additional profile fields"""
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username


class DietaryPreference(models.Model):
    """Model for various dietary preferences/restrictions"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name


class UserDietaryPreference(models.Model):
    """Many-to-many relationship between users and dietary preferences"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dietary_preferences')
    dietary_preference = models.ForeignKey(DietaryPreference, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('user', 'dietary_preference')
    
    def __str__(self):
        return f"{self.user.username} - {self.dietary_preference.name}"


class Cuisine(models.Model):
    """Model for cuisines (Italian, Chinese, Mexican, etc.)"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name


class UserCuisinePreference(models.Model):
    """Many-to-many relationship between users and cuisine preferences"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cuisine_preferences')
    cuisine = models.ForeignKey(Cuisine, on_delete=models.CASCADE)
    preference_level = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    
    class Meta:
        unique_together = ('user', 'cuisine')
    
    def __str__(self):
        return f"{self.user.username} - {self.cuisine.name} ({self.preference_level})"


class Restaurant(models.Model):
    """Model for restaurants"""
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    google_place_id = models.CharField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    price_level = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(4)], null=True, blank=True)
    rating = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(5)], null=True, blank=True)
    rating_count = models.IntegerField(default=0)
    
    def __str__(self):
        return self.name


class RestaurantCuisine(models.Model):
    """Many-to-many relationship between restaurants and cuisines"""
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='cuisines')
    cuisine = models.ForeignKey(Cuisine, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('restaurant', 'cuisine')
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.cuisine.name}"


class FavoriteRestaurant(models.Model):
    """Model for users' favorite restaurants"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_restaurants')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('user', 'restaurant')
    
    def __str__(self):
        return f"{self.user.username} - {self.restaurant.name}"


class GroceryStore(models.Model):
    """Model for grocery stores/supermarkets"""
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    google_place_id = models.CharField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    store_type = models.CharField(max_length=50, blank=True)  # e.g., Asian, Korean, General
    
    def __str__(self):
        return self.name


class FavoriteGroceryStore(models.Model):
    """Model for users' favorite grocery stores"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_grocery_stores')
    grocery_store = models.ForeignKey(GroceryStore, on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'grocery_store')
    
    def __str__(self):
        return f"{self.user.username} - {self.grocery_store.name}"


class Ingredient(models.Model):
    """Model for recipe ingredients"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='ingredients/', null=True, blank=True)
    
    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Model for cooking recipes"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructions = models.TextField()
    prep_time = models.IntegerField(help_text="Preparation time in minutes")
    cook_time = models.IntegerField(help_text="Cooking time in minutes")
    servings = models.IntegerField(default=4)
    difficulty = models.CharField(max_length=20, choices=[
        ('EASY', 'Easy'),
        ('MEDIUM', 'Medium'),
        ('HARD', 'Hard'),
    ])
    image = models.ImageField(upload_to='recipes/', null=True, blank=True)
    source_url = models.URLField(blank=True)
    api_id = models.CharField(max_length=100, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    cuisines = models.ManyToManyField(Cuisine, related_name='recipes')
    
    def __str__(self):
        return self.title


class RecipeIngredient(models.Model):
    """Model for ingredients in a recipe with quantity"""
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.CharField(max_length=50)  # e.g., "2 tablespoons", "1 cup"
    optional = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('recipe', 'ingredient')
    
    def __str__(self):
        return f"{self.recipe.title} - {self.ingredient.name}"


class FavoriteRecipe(models.Model):
    """Model for users' favorite recipes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_recipes')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'recipe')
    
    def __str__(self):
        return f"{self.user.username} - {self.recipe.title}"


class ShoppingList(models.Model):
    """Model for user shopping lists"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shopping_lists')
    name = models.CharField(max_length=100, default="Shopping List")
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"


class ShoppingListItem(models.Model):
    """Model for items in a shopping list"""
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name='items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, null=True, blank=True)
    custom_item = models.CharField(max_length=100, blank=True)  # For items not in the ingredients database
    quantity = models.CharField(max_length=50, blank=True)
    is_purchased = models.BooleanField(default=False)
    
    def __str__(self):
        item_name = self.ingredient.name if self.ingredient else self.custom_item
        return f"{self.shopping_list.name} - {item_name}"


class Post(models.Model):
    """Model for social media posts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    image = models.ImageField(upload_to='posts/', null=True, blank=True)
    date_posted = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    location = models.CharField(max_length=100, blank=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    recipe = models.ForeignKey(Recipe, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    meal_type = models.CharField(max_length=20, choices=[
        ('BREAKFAST', 'Breakfast'),
        ('LUNCH', 'Lunch'),
        ('DINNER', 'Dinner'),
        ('DESSERT', 'Dessert'),
        ('SNACK', 'Snack'),
        ('OTHER', 'Other'),
    ], default='OTHER')
    
    def __str__(self):
        return f"{self.user.username} - {self.date_posted.strftime('%Y-%m-%d %H:%M')}"


class Like(models.Model):
    """Model for likes on posts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    date_liked = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'post')
    
    def __str__(self):
        return f"{self.user.username} liked {self.post.user.username}'s post"


class Comment(models.Model):
    """Model for comments on posts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    date_commented = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} on {self.post.user.username}'s post"


class Follow(models.Model):
    """Model for user following relationships"""
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    followed = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    date_followed = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('follower', 'followed')
    
    def __str__(self):
        return f"{self.follower.username} follows {self.followed.username}"


class Notification(models.Model):
    """Model for user notifications"""
    NOTIFICATION_TYPES = [
        ('LIKE', 'Like'),
        ('COMMENT', 'Comment'),
        ('FOLLOW', 'Follow'),
        ('SYSTEM', 'System Message'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.notification_type} for {self.user.username}"


class UserSearch(models.Model):
    """Model to store user search history"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='searches')
    query = models.CharField(max_length=255)
    search_type = models.CharField(max_length=20, choices=[
        ('RESTAURANT', 'Restaurant'),
        ('RECIPE', 'Recipe'),
        ('GROCERY', 'Grocery Store'),
        ('USER', 'User'),
    ])
    date_searched = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.query} ({self.search_type})"


class TasteProfile(models.Model):
    """Model for AI-generated user taste profiles"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='taste_profile')
    likes_spicy = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    likes_sweet = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    likes_savory = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    likes_healthy = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    likes_comfort_food = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    prefers_budget = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    dining_frequency = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    cooking_frequency = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=3)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Taste Profile"