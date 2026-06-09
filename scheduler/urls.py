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
    path('patients/<int:pk>/session/add/', views.patient_add_session, name='patient_add_session'),
    path('patients/<int:pk>/session/undo/', views.patient_undo_session, name='patient_undo_session'),

    path('api/place/', views.api_place, name='api_place'),
    path('api/unassign/', views.api_unassign, name='api_unassign'),
    path('api/reserve/', views.api_reserve, name='api_reserve'),
    path('api/unreserve/', views.api_unreserve, name='api_unreserve'),
    path('api/toggle-fixed/', views.api_toggle_fixed, name='api_toggle_fixed'),

    path('therapists/', views.therapists, name='therapists'),
    path('stats/', views.stats, name='stats'),
    path('emr/', views.emr_record, name='emr_record'),
    path('import/', views.import_excel, name='import'),
]
