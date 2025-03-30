from django.db import models
from django.db import models

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Men', 'Men'),
        ('Women', 'Women'),
        ('Kids', 'Kids'),
        ('Accessories', 'Accessories'),
    ]
    STYLE_CHOICES = [
    ("Casual", "Casual"),
    ("Party", "Party"),
    ("Formal", "Formal"),
]
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    style_type = models.CharField(max_length=20, choices=STYLE_CHOICES, default="Casual")
    image = models.ImageField(upload_to='')  # Saves directly inside media/
# Image upload
    is_trending = models.BooleanField(default=False)

    def __str__(self):
        return self.name
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=100)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
from django.contrib.auth.models import User
from django.db import models
from django.contrib.auth.models import User
import uuid
from django.conf import settings  # ✅ Correct!

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,null=True, on_delete=models.CASCADE)  # ✅ Correct!
 # Allow user to be null
    cart_id = models.CharField(max_length=255, null=True, blank=True)  # For anonymous users
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def subtotal(self):
        return self.quantity * self.product.price  # Assuming 'price' is in Product model

    def __str__(self):
        return f"{self.user.username if self.user else self.cart_id} - {self.product.name} ({self.quantity})"

from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # Add any extra fields here, if needed
    pass

    