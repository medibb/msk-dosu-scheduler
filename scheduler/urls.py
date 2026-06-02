from django.urls import path

from . import auth, views

urlpatterns = [
    path('login/', auth.login_view, name='login'),
    path('logout/', auth.logout_view, name='logout'),

    path('', views.schedule, name='schedule'),
    path('waitlist/', views.waitlist, name='waitlist'),

    path('patients/new/', views.patient_create, name='patient_create'),
    path('patients/<int:pk>/', views.patient_detail, name='patient_detail'),
    path('patients/<int:pk>/edit/', views.patient_edit, name='patient_edit'),
    path('patients/<int:pk>/status/', views.patient_set_status, name='patient_set_status'),

    path('stats/', views.stats, name='stats'),
    path('import/', views.import_excel, name='import'),
]
