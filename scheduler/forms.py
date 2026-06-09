from django import forms

from .models import Patient


class PatientForm(forms.ModelForm):
    """환자 등록/수정 폼(v2 간략화).

    처방코드·외래·진료과·담당치료사·상태는 입력하지 않는다.
    - 처방코드 → 부위/단계(category) 8분류 선택('기타'는 직접 입력)
    - 담당치료사/상태는 주간 시간표 drag&drop으로 결정(상태 기본 대기중)
    """
    class Meta:
        model = Patient
        fields = [
            'registration_number', 'name', 'age', 'sex',
            'prescription_date', 'category', 'category_etc',
            'memo', 'phone', 'preferred_days', 'preferred_times',
            'target_sessions', 'completion_eval_date', 'note',
            'last_contact_date', 'contact_result',
        ]
        widgets = {
            'prescription_date': forms.DateInput(attrs={'type': 'date'}),
            'completion_eval_date': forms.DateInput(attrs={'type': 'date'}),
            'last_contact_date': forms.DateInput(attrs={'type': 'date'}),
            'category_etc': forms.TextInput(attrs={'placeholder': "'기타' 선택 시 직접 입력"}),
            'note': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        cleaned = super().clean()
        # '기타'가 아니면 기타 입력값은 비운다.
        if cleaned.get('category') != 'etc':
            cleaned['category_etc'] = ''
        return cleaned
