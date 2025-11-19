from django.urls import path
from . import views

urlpatterns = [
    # "категорії" = кореневі вузли дерева
    path("categories/", views.get_categories, name="get_categories"),
    # "підкатегорії" = діти обраного вузла
    path("subcategories/<int:category_id>/", views.get_subcategories, name="get_subcategories"),
    # інструкції, привʼязані до конкретного вузла
    path("instructions/<int:subcategory_id>/", views.get_instructions, name="get_instructions"),
    # деталі інструкції
    path("instruction/<int:instruction_id>/", views.get_instruction_detail, name="get_instruction_detail"),
    # пошук
    path("search_instructions/", views.search_instructions, name="search_instructions"),
]
