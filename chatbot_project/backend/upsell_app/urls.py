from django.urls import path
from . import views

urlpatterns = [
    path("cross/text/", views.cross_text),
    path("change/search/", views.change_search),
    path("accessories/categories/", views.accessories_categories),
    path("accessories/category/<int:category_id>/text/", views.accessories_category_text),
]
