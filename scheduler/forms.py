from django import forms

from .models import Patient


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'registration_number', 'name', 'age', 'sex',
            'prescription_date', 'prescription_code', 'is_outpatient',
            'memo', 'department', 'therapist', 'status',
            'phone', 'preferred_days', 'preferred_times',
            'target_sessions', 'completion_eval_date', 'note',
            'last_contact_date', 'contact_result',
        ]
        widgets = {
            'prescription_date': forms.DateInput(attrs={'type': 'date'}),
            'completion_eval_date': forms.DateInput(attrs={'type': 'date'}),
            'last_contact_date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 2}),
        }
