import json

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import PatientForm
from .models import Appointment, Patient, Settings, Status, Therapist
from .services import schedule as sch

# 상태 흐름: 다음 단계로 한 번에 전진
NEXT_STATUS = {
    Status.WAITING: Status.BOOKED,
    Status.BOOKED: Status.ONGOING,
    Status.ONGOING: Status.DONE,
}


def schedule(request):
    """주간 시간표 그리드. 치료사별 보기 + 대기자 드래그 소스."""
    therapists = list(Therapist.objects.filter(is_active=True))
    if not therapists:
        return render(request, 'schedule.html', {'no_therapist': True})

    tid = request.GET.get('therapist')
    current = next((t for t in therapists if str(t.id) == tid), therapists[0])

    grid = sch.build_grid(current)
    # 드래그 소스: 아직 배정 안 된(대기중) 환자 + 이 치료사 배정 환자
    waitlist = Patient.objects.filter(status=Status.WAITING).order_by('-prescription_date')[:100]

    return render(request, 'schedule.html', {
        'therapists': therapists,
        'current': current,
        'grid': grid,
        'weekdays': ['월', '화', '수', '목', '금'],
        'waitlist': waitlist,
    })


def _json_patient_card(appt):
    p = appt.patient
    return {
        'appointment_id': appt.pk,
        'patient_id': p.pk,
        'name': p.name,
        'memo': p.memo,
        'sessions': f'{p.session_count}/{p.target_sessions}',
        'is_fixed': appt.is_fixed,
    }


@require_POST
def api_place(request):
    """대기자→칸 배정 또는 칸 이동. JSON: patient_id, therapist_id, weekday, slot_index, appointment_id?"""
    try:
        data = json.loads(request.body)
        patient = get_object_or_404(Patient, pk=data['patient_id'])
        therapist = get_object_or_404(Therapist, pk=data['therapist_id'])
        appt = None
        if data.get('appointment_id'):
            appt = get_object_or_404(Appointment, pk=data['appointment_id'])
        appt = sch.place(patient, therapist,
                         int(data['weekday']), int(data['slot_index']), appointment=appt)
    except sch.ScheduleConflict as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=409)
    except (KeyError, ValueError) as e:
        return JsonResponse({'ok': False, 'error': f'잘못된 요청: {e}'}, status=400)
    return JsonResponse({'ok': True, 'card': _json_patient_card(appt)})


@require_POST
def api_unassign(request):
    """그리드에서 배정 제거(대기자로 복귀). JSON: appointment_id."""
    data = json.loads(request.body)
    appt = get_object_or_404(Appointment, pk=data['appointment_id'])
    sch.unassign(appt)
    return JsonResponse({'ok': True})


@require_POST
def api_toggle_fixed(request):
    """스케줄 고정 토글. JSON: appointment_id."""
    data = json.loads(request.body)
    appt = get_object_or_404(Appointment, pk=data['appointment_id'])
    return JsonResponse({'ok': True, 'is_fixed': sch.toggle_fixed(appt)})


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
