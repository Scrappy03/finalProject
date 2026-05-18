from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('login/', views.SanctuaryLoginView.as_view(), name='login'),
    path('logout/', views.SanctuaryLogoutView.as_view(), name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('entries/new/', views.entry_create, name='entry_create'),
    path('insights/', views.insights, name='insights'),
    path('goals/', views.goals, name='goals'),
    path('report/', views.report, name='report'),
]
