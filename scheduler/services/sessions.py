"""회차/진행 추적: 회차 기록, 종결평가 대상 조회, 종결 처리."""
from django.utils import timezone

from ..models import Patient, Session, Status


def add_session(patient, on_date=None):
    """다음 회차를 기록. 첫 회차면 시작일/시행중으로 전환."""
    on_date = on_date or timezone.localdate()
    next_num = patient.session_count + 1
    session = Session.objects.create(patient=patient, number=next_num, date=on_date)

    fields = []
    if patient.status in (Status.WAITING, Status.BOOKED):
        patient.status = Status.ONGOING
        fields.append('status')
    if not patient.start_date:
        patient.start_date = on_date
        fields.append('start_date')
    if fields:
        fields.append('updated_at')
        patient.save(update_fields=fields)
    return session


def remove_last_session(patient):
    """마지막 회차 1건 취소(오기록 정정용)."""
    last = patient.sessions.order_by('-number').first()
    if last:
        last.delete()
    return last


def complete(patient, on_date=None):
    """종결 처리: 상태 종결 + 종결일 기록."""
    patient.status = Status.DONE
    patient.end_date = on_date or timezone.localdate()
    patient.save(update_fields=['status', 'end_date', 'updated_at'])
    return patient


def completion_due():
    """종결 목표 회차에 도달했지만 아직 종결되지 않은 환자 목록."""
    due = []
    qs = Patient.objects.exclude(status=Status.DONE).prefetch_related('sessions')
    for p in qs:
        if p.session_count >= p.target_sessions:
            due.append(p)
    return due
