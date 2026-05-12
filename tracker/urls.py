from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('entries/new/', views.entry_create, name='entry_create'),
    path('report/', views.report, name='report'),
]
