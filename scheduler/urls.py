from django.urls import path

from . import auth, views

urlpatterns = [
    path('login/', auth.login_view, name='login'),
    path('logout/', auth.logout_view, name='logout'),
    path('', views.schedule, name='schedule'),
    path('waitlist/', views.waitlist, name='waitlist'),
    path('stats/', views.stats, name='stats'),
    path('import/', views.import_excel, name='import'),
]
