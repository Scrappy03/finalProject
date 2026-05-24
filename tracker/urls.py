from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.SanctuaryLoginView.as_view(), name='login'),
    path('logout/', views.SanctuaryLogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('entries/', views.entry_history, name='entry_history'),
    path('entries/new/', views.entry_create, name='entry_create'),
    path('entries/<int:entry_id>/edit/', views.entry_edit, name='entry_edit'),
    path('trends/', views.trends, name='trends'),
    path('insights/', views.insights, name='insights'),
    path('goals/', views.goals, name='goals'),
    path('settings/', views.settings, name='settings'),
]
