# instructions_app/urls.py
from django.urls import path
from . import views
from .views import search_instructions

urlpatterns = [
    path('categories/', views.get_categories, name='get_categories'),
    path('subcategories/<int:category_id>/', views.get_subcategories, name='get_subcategories'),
    path('instructions/<int:subcategory_id>/', views.get_instructions, name='get_instructions'),
    path('instruction/<int:instruction_id>/', views.get_instruction_detail, name='get_instruction_detail'),
    path('search_instructions/', search_instructions, name='search_instructions'),
]
