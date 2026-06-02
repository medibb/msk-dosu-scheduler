from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import PatientForm
from .models import Patient, Settings, Status, Therapist

# 상태 흐름: 다음 단계로 한 번에 전진
NEXT_STATUS = {
    Status.WAITING: Status.BOOKED,
    Status.BOOKED: Status.ONGOING,
    Status.ONGOING: Status.DONE,
}


def schedule(request):
    """주간 시간표 그리드(상세 구현은 3.0). 현재는 골격."""
    settings_obj = Settings.load()
    return render(request, 'schedule.html', {
        'time_slots': settings_obj.time_slots,
    })


def waitlist(request):
    """대기자/환자 목록: 상태·치료사 필터, 검색, 정렬."""
    qs = Patient.objects.select_related('therapist').all()

    status = request.GET.get('status', '')
    therapist_id = request.GET.get('therapist', '')
    q = request.GET.get('q', '').strip()

    if status:
        qs = qs.filter(status=status)
    if therapist_id:
        qs = qs.filter(therapist_id=therapist_id)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(registration_number__icontains=q))

    return render(request, 'waitlist.html', {
        'patients': qs,
        'therapists': Therapist.objects.filter(is_active=True),
        'status_choices': Status.choices,
        'cur_status': status,
        'cur_therapist': therapist_id,
        'q': q,
    })


def patient_create(request):
    form = PatientForm(request.POST or None)
    if form.is_valid():
        p = form.save()
        messages.success(request, f'{p.name} 환자를 등록했습니다.')
        return redirect('patient_detail', pk=p.pk)
    return render(request, 'patient_form.html', {'form': form, 'is_new': True})


def patient_edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    form = PatientForm(request.POST or None, instance=patient)
    if form.is_valid():
        form.save()
        messages.success(request, '수정했습니다.')
        return redirect('patient_detail', pk=patient.pk)
    return render(request, 'patient_form.html', {'form': form, 'is_new': False, 'patient': patient})


def patient_detail(request, pk):
    patient = get_object_or_404(
        Patient.objects.select_related('therapist').prefetch_related('sessions'), pk=pk)
    return render(request, 'patient_detail.html', {
        'patient': patient,
        'next_status': NEXT_STATUS.get(patient.status),
    })


def patient_set_status(request, pk):
    """상태를 지정 값(또는 다음 단계)으로 전환. 종결 시 종결일 자동 기록."""
    patient = get_object_or_404(Patient, pk=pk)
    target = request.POST.get('status') or NEXT_STATUS.get(patient.status)
    if target in Status.values:
        patient.status = target
        if target == Status.DONE and not patient.end_date:
            patient.end_date = timezone.localdate()
        patient.save(update_fields=['status', 'end_date', 'updated_at'])
        messages.success(request, f'{patient.name} → {target}')
    return redirect(request.POST.get('next') or reverse('patient_detail', args=[pk]))


def stats(request):
    """통계(상세 구현은 5.0)."""
    return render(request, 'placeholder.html', {'title': '통계'})


def import_excel(request):
    """엑셀 업로드 → 일괄 등록(중복 건너뜀)."""
    from .services import import_excel as ie

    if request.method == 'POST' and request.FILES.get('file'):
        try:
            result = ie.import_patients(request.FILES['file'])
            messages.success(
                request,
                f"등록 {result['created']}건, 중복 건너뜀 {result['skipped']}건 (총 {result['total']}건)")
            return redirect('waitlist')
        except Exception as e:  # noqa: BLE001 — 사용자에게 오류 메시지 노출
            messages.error(request, f'엑셀을 읽을 수 없습니다: {e}')
    return render(request, 'import.html', {})
