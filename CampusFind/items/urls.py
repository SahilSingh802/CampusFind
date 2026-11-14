from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('lost/', views.lost_items, name='lost_items'),
    path('found/', views.found_items, name='found_items'),
    path('search/', views.search_items, name='search'),
    path('item/<int:pk>/', views.item_detail, name='item_detail'),
    path('item/<int:pk>/save/', views.toggle_saved_item, name='toggle_saved_item'),

    # Reporting (dynamic URL parameters)
    path('report/<str:item_type>/', views.report_item, name='report_item'),
    path('item/<int:pk>/edit/', views.edit_item, name='edit_item'),
    path('item/<int:pk>/delete/', views.delete_item, name='delete_item'),
    path('item/<int:pk>/status/', views.update_item_status, name='update_item_status'),

    # Claims
    path('item/<int:pk>/claim/', views.claim_item, name='claim_item'),
    path('claim/<int:pk>/<str:action>/', views.review_claim, name='review_claim'),

    # Authentication
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html',
                                                redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),
]
