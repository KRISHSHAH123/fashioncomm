from django.urls import path
from .views import index, product_detail, search_by_image,shop,chatbot_view
from .views import get_similar_products
from .views import view_cart, add_to_cart, update_cart,remove_from_cart, signup_view,login_view
from django.contrib.auth.views import LoginView  # ✅ Correct


urlpatterns = [
    path("", index, name="index"),
    path("product/<int:product_id>/", product_detail, name="product_detail"),
      path("search/", search_by_image, name="search"),
      path("shop/", shop, name="shop"),
          path('chatbot/', chatbot_view, name='chatbot'),
            path("get_similar_products/", get_similar_products, name="get_similar_products"),
    path('view-cart/', view_cart, name='view_cart'),
    path('add-to-cart/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('update-cart/<int:product_id>/', update_cart, name='update_cart'),
    path('remove-cart/<int:product_id>/', remove_from_cart, name='remove_from_cart'),
       path('login/', LoginView.as_view(template_name='shop/login.html'), name='login'),
     path("signup/", signup_view, name="signup"),
    # path('login/', login_view, name='login'),
    # path('logout/', logout_view, name='logout'),  
    

]

