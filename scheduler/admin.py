from django.contrib import admin

from .models import Appointment, Patient, Session, Settings, Therapist


@admin.register(Therapist)
class TherapistAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'order')
    list_editable = ('is_active', 'order')


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'registration_number', 'status', 'therapist',
                    'prescription_code', 'session_count', 'target_sessions',
                    'prescription_date')
    list_filter = ('status', 'therapist', 'prescription_code')
    search_fields = ('name', 'registration_number')
    date_hierarchy = 'prescription_date'


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'therapist', 'weekday', 'slot_index', 'is_fixed')
    list_filter = ('therapist', 'weekday', 'is_fixed')


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('patient', 'number', 'date')
    list_filter = ('date',)


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ('id',)
