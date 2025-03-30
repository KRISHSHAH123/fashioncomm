import os
import json
import pickle
import numpy as np
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from sklearn.metrics.pairwise import cosine_similarity
from .models import Product


# Home Page - Show Trending Products
def index(request):
    trending_products = Product.objects.filter(is_trending=True)[:6]  # Show 6 trending products
    return render(request, "shop/index.html", {"trending_products": trending_products})


# Product Detail Page
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'shop/product_detail.html', {'product': product})


# Shop Page - Show All Products
def shop(request):
    products = Product.objects.all()
    return render(request, 'shop/shop.html', {'products': products})


# Chatbot API
@csrf_exempt  # Consider using @csrf_protect in production
def chatbot_view(request):
    if request.method != "POST":
        return JsonResponse({"response": "Invalid request method."}, status=400)

    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").lower()

        # Response Logic
        responses = {
            ("hello", "hi", "hey"): "Hey! Welcome to our fashion store. How can I help you today?",
            ("support",): "I’d be happy to assist you! Do you need help with order tracking, pricing, or something else?",
            ("order", "track"): "Sure! Please provide your order ID, and I'll check the status for you.",
            ("price", "cost"): "Our prices vary by item. What product are you interested in?",
            ("recommend", "suggest"): "Tell me about your mood—are you looking for casual, party, or formal outfits?",
            ("casual",): "Here are some trendy casual outfits for you: []",
            ("party",): "Here are some stylish party outfits for you: [link-to-party-fashion]",
            ("formal",): "Here are some elegant formal outfits for you: [link-to-formal-fashion]"
        }

        bot_response = "I'm sorry, I didn't quite get that. Could you rephrase your request?"
        for keywords, response in responses.items():
            if any(word in user_message for word in keywords):
                bot_response = response
                break

        return JsonResponse({"response": bot_response})

    except Exception as e:
        return JsonResponse({"response": "An error occurred. Please try again later."}, status=500)


def shop_view(request):
    # Get query parameters
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', 'all')

    # Start with all products
    products = Product.objects.all()

    # Apply search filter if search query exists
    if search_query:
        products = products.filter(name__icontains=search_query)

    # Apply category filter if not 'all'
    if category_filter != 'all':
        products = products.filter(category=category_filter)

    context = {
        'products': products,
        'current_search': search_query,
        'current_category': category_filter
    }

    return render(request, 'shop.html', context)

# Image-Based Search
def search_by_image(request):
    if request.method == "POST":
        image = request.FILES.get("image")

        if not image:
            return JsonResponse({"error": "No image uploaded"}, status=400)

        # (For now, just show all products as results)
        products = Product.objects.all()
        return render(request, "shop/home.html", {"products": products})

    return render(request, "shop/search.html")
import os
import pickle
import faiss
import numpy as np
from django.http import JsonResponse
from django.conf import settings
import logging
from .models import Product  # Import your Product model

logger = logging.getLogger(__name__)

def get_similar_products(request):
    """
    Returns a list of similar products based on image feature similarity.
    """
    # Define paths
    feature_file = os.path.join(settings.MEDIA_ROOT, "image_features.pkl")
    faiss_index_file = os.path.join(settings.MEDIA_ROOT, "faiss_index.bin")

    # Load feature data
    try:
        with open(feature_file, "rb") as f:
            data = pickle.load(f)
            all_features = data["features"]
            image_names = data["names"]
    except Exception as e:
        logger.error(f"Error loading features: {e}")
        return JsonResponse({"error": "Unable to load feature data"}, status=500)

    # Get query image
    product_image = request.GET.get("image", "").strip()
    if not product_image:
        return JsonResponse({"error": "No image provided"}, status=400)

    # Normalize filenames for case-insensitive matching
    image_names_lower = [name.lower() for name in image_names]
    if product_image.lower() not in image_names_lower:
        logger.warning(f"Query image '{product_image}' not found in feature data")
        return JsonResponse({"error": f"Image '{product_image}' not found"}, status=404)

    idx = image_names_lower.index(product_image.lower())
    product_image = image_names[idx]  # Preserve original case

    # Get the query product's name
    try:
        query_product = Product.objects.get(image=product_image)
        query_product_name = query_product.name
    except Product.DoesNotExist:
        query_product_name = "Unknown Product"
        logger.warning(f"Query product not found for image: {product_image}")

    # Load FAISS index
    try:
        index = faiss.read_index(faiss_index_file)
    except Exception as e:
        logger.error(f"Error loading FAISS index: {e}")
        return JsonResponse({"error": "FAISS index not found"}, status=500)

    # Perform similarity search
    query_vector = np.array([all_features[idx]], dtype=np.float32)
    distances, indices = index.search(query_vector, 6)  # Get top 6 results

    logger.info(f"FAISS search results for '{product_image}': {list(zip(indices[0], distances[0]))}")

    # Build similar product list
    similar_products = []
    for i, dist in zip(indices[0], distances[0]):
        candidate = image_names[i]
        if candidate == product_image:  # Skip the query image itself
            continue
        if dist < 300:  # Adjusted Threshold (Experiment with 100-500)
            try:
                # Fetch the product using the image filename
                product = Product.objects.get(image=candidate)
                similar_products.append({
                    "image": f"/media/{candidate}",  # Serve via Django static/media
                    "name": product.name,  # Use the product's name from the database
                    "url": f"/product/{product.id}"  # Use the product's ID
                })
            except Product.DoesNotExist:
                logger.warning(f"Product not found for image: {candidate}")
                continue  # Skip if no product is found

    if not similar_products:
        logger.warning(f"No recommendations found for '{product_image}'")
        return JsonResponse({
            "query_image": product_image,
            "query_name": query_product_name,  # Include the query product name
            "similar_products": []
        })

    return JsonResponse({
        "query_image": product_image,
        "query_name": query_product_name,  # Include the query product name
        "similar_products": similar_products
    })

from django.contrib.auth.decorators import login_required
from .models import Cart
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404, redirect
from .models import Cart, Product
import uuid

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # If the user is authenticated, use their user ID, otherwise use session-based cart_id
    if request.user.is_authenticated:
        cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)
    else:
        # For anonymous users, use the session cart_id
        cart_id = request.session.get('cart_id', None)
        if not cart_id:
            cart_id = str(uuid.uuid4())  # Create a unique cart identifier
            request.session['cart_id'] = cart_id

        cart_item, created = Cart.objects.get_or_create(cart_id=cart_id, product=product)

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    # Always redirect to the cart, no JSON
    return redirect('view_cart')


@login_required
def update_cart(request, product_id):
    """Update the quantity of a product in the cart"""
    product = get_object_or_404(Product, id=product_id)
    cart_item = Cart.objects.filter(user=request.user, product=product).first()

    if cart_item:
        new_quantity = int(request.POST.get("quantity", 1))
        if new_quantity > 0:
            cart_item.quantity = new_quantity
            cart_item.save()
        else:
            cart_item.delete()

        return JsonResponse({"message": "Cart updated", "quantity": cart_item.quantity})
    
    return JsonResponse({"error": "Product not in cart"}, status=400)

@login_required
def remove_from_cart(request, product_id):
    """Remove a product from the cart"""
    product = get_object_or_404(Product, id=product_id)
    cart_item = Cart.objects.filter(user=request.user, product=product).first()

    if cart_item:
        cart_item.delete()
        return JsonResponse({"message": "Product removed from cart"})

    return JsonResponse({"error": "Product not in cart"}, status=400)

@login_required
def view_cart(request):
    """Display the cart contents"""
    cart_items = Cart.objects.filter(user=request.user)
    total_price = sum(item.subtotal() for item in cart_items)

    return render(request, "cart.html", {"cart_items": cart_items, "total_price": total_price})
from  django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import CustomUserCreationForm
# from django.contrib.auth import login,logout
# def register(request):
#     if request.method =='POST':
#         form = UserCreationForm(request.POST)
#         if form.is_valid():
#             user=form.save()
#             login(request,user)
#             return redirect('index')
#     else:
#         form = UserCreationForm()
#     return render(request, 'register.html', {'form': form})
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.contrib import messages

def login_view(request):
    form = AuthenticationForm()

    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Login successful!")

            # ✅ Check if 'next' exists in the request to handle redirection correctly
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)  # Redirect to the intended page

            return redirect('index')  # ✅ Redirect to homepage (update 'index' with your actual homepage URL name)

        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "shop/login.html", {"form": form})
  # Render form
def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Your account was created successfully!")
            return redirect('index')
        else:
            print(form.errors)  # 👈 Print errors in the console
            messages.error(request, "There was an error with your signup. Please try again.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})

