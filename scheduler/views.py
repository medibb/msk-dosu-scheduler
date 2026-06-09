import json
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Count, Q
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
    """주간 시간표 그리드. 전체 보기(기본) + 치료사별 보기 + 예약 대기칸 + 대기자."""
    therapists = list(Therapist.objects.filter(is_active=True))
    if not therapists:
        return render(request, 'schedule.html', {'no_therapist': True})

    # 대기자: 대기일수(처방일 기준, 없으면 등록일) 계산 후 오래 기다린 순 정렬
    today = timezone.localdate()
    waitlist = list(Patient.objects.filter(status=Status.WAITING))
    for p in waitlist:
        base = p.prescription_date or timezone.localtime(p.created_at).date()
        p.wait_days = (today - base).days
    waitlist.sort(key=lambda p: p.wait_days, reverse=True)

    ctx = {
        'therapists': therapists,
        'weekdays': ['월', '화', '수', '목', '금'],
        'waitlist': waitlist,
        'reservation_rows': sch.build_reservation_grid(),
    }

    tid = request.GET.get('therapist')
    current = next((t for t in therapists if str(t.id) == tid), None)
    if current is not None:
        # 치료사별 보기
        ctx.update(view='single', current=current, grid=sch.build_grid(current))
    else:
        # 전체 보기(기본): 요일×치료사
        ctx.update(view='all', grid_all=sch.build_grid_all(therapists))
    return render(request, 'schedule.html', ctx)


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
def api_reserve(request):
    """예약 대기칸에 환자 등록. JSON: patient_id, weekday, period(0=오전,1=오후)."""
    try:
        data = json.loads(request.body)
        patient = get_object_or_404(Patient, pk=data['patient_id'])
        sch.reserve(patient, int(data['weekday']), int(data['period']))
    except (KeyError, ValueError) as e:
        return JsonResponse({'ok': False, 'error': f'잘못된 요청: {e}'}, status=400)
    return JsonResponse({'ok': True, 'card': {
        'patient_id': patient.pk,
        'name': patient.name,
        'memo': patient.category_label or patient.memo,
    }})


@require_POST
def api_unreserve(request):
    """예약 대기칸에서 환자 제거(대기자로 복귀). JSON: patient_id."""
    data = json.loads(request.body)
    patient = get_object_or_404(Patient, pk=data['patient_id'])
    sch.unreserve(patient)
    return JsonResponse({'ok': True})


@require_POST
def api_toggle_fixed(request):
    """스케줄 고정 토글. JSON: appointment_id."""
    data = json.loads(request.body)
    appt = get_object_or_404(Appointment, pk=data['appointment_id'])
    return JsonResponse({'ok': True, 'is_fixed': sch.toggle_fixed(appt)})


# 대기자 표에서 정렬 가능한 컬럼: 표시 key → ORM 정렬 필드
WAITLIST_SORT_FIELDS = {
    'status': 'status',
    'name': 'name',
    'registration_number': 'registration_number',
    'category': 'category',
    'memo': 'memo',
    'therapist': 'therapist__name',
    'sessions': 'sess_count',          # 아래 annotate로 계산
    'prescription_date': 'prescription_date',
}


def waitlist(request):
    """대기자/환자 목록: 상태·치료사 필터, 검색, 컬럼별 오름/내림 정렬."""
    from .services import sessions as ssvc

    qs = Patient.objects.select_related('therapist').annotate(sess_count=Count('sessions'))

    status = request.GET.get('status', '')
    therapist_id = request.GET.get('therapist', '')
    q = request.GET.get('q', '').strip()
    due_only = request.GET.get('due') == '1'
    sort = request.GET.get('sort', '')
    direction = request.GET.get('dir', '')

    if status:
        qs = qs.filter(status=status)
    if therapist_id:
        qs = qs.filter(therapist_id=therapist_id)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(registration_number__icontains=q))

    due = ssvc.completion_due()
    if due_only:
        qs = qs.filter(pk__in=[p.pk for p in due])

    # 정렬: 유효한 컬럼이면 그 기준(오름/내림), 아니면 기본(처방일 내림차순)
    if sort in WAITLIST_SORT_FIELDS:
        if direction not in ('asc', 'desc'):
            direction = 'asc'
        prefix = '' if direction == 'asc' else '-'
        qs = qs.order_by(prefix + WAITLIST_SORT_FIELDS[sort], 'name')
    else:
        sort, direction = '', ''
        qs = qs.order_by('-prescription_date', 'name')

    # 헤더용 정렬 링크: 현재 필터를 유지하고, 클릭 시 방향을 토글한다.
    base = {}
    if status:
        base['status'] = status
    if therapist_id:
        base['therapist'] = therapist_id
    if q:
        base['q'] = q
    if due_only:
        base['due'] = '1'
    sort_links = {}
    for key in WAITLIST_SORT_FIELDS:
        params = dict(base, sort=key)
        params['dir'] = 'desc' if (sort == key and direction == 'asc') else 'asc'
        arrow = ('▲' if direction == 'asc' else '▼') if sort == key else ''
        sort_links[key] = {'url': '?' + urlencode(params), 'arrow': arrow}

    return render(request, 'waitlist.html', {
        'patients': qs,
        'therapists': Therapist.objects.filter(is_active=True),
        'status_choices': Status.choices,
        'cur_status': status,
        'cur_therapist': therapist_id,
        'q': q,
        'due_count': len(due),
        'due_only': due_only,
        'sort_links': sort_links,
        'cur_sort': sort,
        'cur_dir': direction,
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
        'sessions': patient.sessions.all(),
    })


@require_POST
def patient_add_session(request, pk):
    """회차 +1 기록(오늘 날짜). 첫 회차면 시행중 전환."""
    from .services import sessions as ssvc
    patient = get_object_or_404(Patient, pk=pk)
    s = ssvc.add_session(patient)
    messages.success(request, f'{patient.name} {s.number}회차 기록')
    return redirect(request.POST.get('next') or reverse('patient_detail', args=[pk]))


@require_POST
def patient_undo_session(request, pk):
    """마지막 회차 취소(오기록 정정)."""
    from .services import sessions as ssvc
    patient = get_object_or_404(Patient, pk=pk)
    ssvc.remove_last_session(patient)
    messages.success(request, '마지막 회차를 취소했습니다.')
    return redirect(reverse('patient_detail', args=[pk]))


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


def _stats_period(request):
    """쿼리스트링에서 기간을 해석. 기본: 이번 달."""
    from datetime import date
    import calendar
    today = timezone.localdate()
    preset = request.GET.get('preset', 'month')
    start_s, end_s = request.GET.get('start'), request.GET.get('end')
    if start_s and end_s:
        try:
            return date.fromisoformat(start_s), date.fromisoformat(end_s), 'custom'
        except ValueError:
            pass
    if preset == 'year':
        return date(today.year, 1, 1), date(today.year, 12, 31), 'year'
    if preset == 'quarter':
        q = (today.month - 1) // 3
        start = date(today.year, q * 3 + 1, 1)
        end_month = q * 3 + 3
        end = date(today.year, end_month, calendar.monthrange(today.year, end_month)[1])
        return start, end, 'quarter'
    # month
    last = calendar.monthrange(today.year, today.month)[1]
    return date(today.year, today.month, 1), date(today.year, today.month, last), 'month'


def stats(request):
    """기간별·처방코드/치료사/부위별 도수치료 건수 집계."""
    from .services import stats as svc
    start, end, preset = _stats_period(request)
    data = svc.aggregate(start, end)

    if request.GET.get('format') == 'csv':
        from django.http import HttpResponse
        resp = HttpResponse(svc.to_csv(data), content_type='text/csv; charset=utf-8-sig')
        resp['Content-Disposition'] = f'attachment; filename="stats_{start}_{end}.csv"'
        return resp

    return render(request, 'stats.html', {'data': data, 'preset': preset})


def emr_record(request):
    """선행치료 경과 기록 생성 패널.

    EMR과 직접 연동하지 않고, 도수치료 전환 근거가 되는 '선행치료 경과' 기록을
    표준 양식으로 생성·표시하고 클립보드로 복사할 수 있게 한다(복붙용).
    기록은 저장하지 않는 무상태(stateless) 도구라 모든 조립은 클라이언트에서 한다.
    """
    today = timezone.localdate()
    return render(request, 'emr_record.html', {
        'today': today.isoformat(),
        'end_default': (today + timedelta(days=13)).isoformat(),  # D0~D13 ≈ 2주
    })


def therapists(request):
    """치료사 관리: 추가 / 이름변경 / 정렬 / 활성토글 / 삭제.

    공용 1계정 환경이라 별도 admin 로그인 없이 쓰도록 간이 화면으로 제공한다.
    삭제 시 해당 치료사의 시간표 배정(Appointment)은 함께 사라지고,
    환자의 담당치료사는 비워진다(모델의 on_delete 정책).
    """
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            name = request.POST.get('name', '').strip()
            if not name:
                messages.error(request, '치료사 이름을 입력하세요.')
            elif Therapist.objects.filter(name=name).exists():
                messages.error(request, f'이미 등록된 치료사입니다: {name}')
            else:
                Therapist.objects.create(name=name, order=Therapist.objects.count())
                messages.success(request, f'치료사를 추가했습니다: {name}')

        elif action == 'update':
            t = get_object_or_404(Therapist, pk=request.POST.get('id'))
            name = request.POST.get('name', '').strip()
            if not name:
                messages.error(request, '이름은 비울 수 없습니다.')
            elif Therapist.objects.filter(name=name).exclude(pk=t.pk).exists():
                messages.error(request, f'이미 등록된 이름입니다: {name}')
            else:
                t.name = name
                t.is_active = request.POST.get('is_active') == 'on'
                try:
                    t.order = int(request.POST.get('order', t.order))
                except (TypeError, ValueError):
                    pass
                t.save()
                messages.success(request, f'수정했습니다: {t.name}')

        elif action == 'delete':
            t = get_object_or_404(Therapist, pk=request.POST.get('id'))
            name = t.name
            t.delete()
            messages.success(request, f'삭제했습니다: {name}')

        return redirect('therapists')

    return render(request, 'therapists.html', {
        'therapists': Therapist.objects.all(),
    })


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
