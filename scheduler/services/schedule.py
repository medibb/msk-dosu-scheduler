"""주간 시간표 그리드 로직: 시간대 구성, 배정/이동/해제, 충돌 방지, 예약 대기칸."""
from ..models import Appointment, Period, Reservation, Settings, Status, Weekday


class ScheduleConflict(Exception):
    """같은 치료사의 같은 요일·시간대에 이미 배정이 있을 때."""


def get_time_slots():
    return Settings.load().time_slots


def build_grid(therapist):
    """치료사 한 명의 요일(월~금)×시간대 그리드 구조를 만든다."""
    slots = get_time_slots()
    appts = {
        (a.weekday, a.slot_index): a
        for a in Appointment.objects.filter(therapist=therapist).select_related('patient')
    }
    rows = []
    for si, slot in enumerate(slots):
        cells = [
            {'weekday': wd, 'slot_index': si, 'appointment': appts.get((wd, si))}
            for wd in range(len(Weekday.choices))
        ]
        rows.append({'slot': slot, 'slot_index': si, 'cells': cells})
    return rows


def build_grid_all(therapists):
    """전체 보기: 요일×치료사로 열을 펼친 그리드. 각 칸은 (치료사, 요일, 시간대)."""
    slots = get_time_slots()
    appts = {
        (a.therapist_id, a.weekday, a.slot_index): a
        for a in Appointment.objects.select_related('patient', 'therapist')
    }
    rows = []
    for si, slot in enumerate(slots):
        cells = []
        for wd in range(len(Weekday.choices)):
            for t in therapists:
                cells.append({
                    'weekday': wd, 'slot_index': si, 'therapist': t,
                    'appointment': appts.get((t.id, wd, si)),
                })
        rows.append({'slot': slot, 'slot_index': si, 'cells': cells})
    return rows


def build_reservation_grid():
    """예약 대기칸: 오전/오후(행) × 요일 월~금(열). 각 칸에 예약 환자 목록."""
    cells = {}
    for r in Reservation.objects.select_related('patient'):
        cells.setdefault((r.weekday, r.period), []).append(r)
    rows = []
    for period, label in Period.choices:
        row = {'period': period, 'label': label, 'cells': []}
        for wd in range(len(Weekday.choices)):
            row['cells'].append({
                'weekday': wd, 'period': period,
                'reservations': cells.get((wd, period), []),
            })
        rows.append(row)
    return rows


def _occupied(therapist, weekday, slot_index, exclude=None):
    qs = Appointment.objects.filter(
        therapist=therapist, weekday=weekday, slot_index=slot_index)
    if exclude is not None:
        qs = qs.exclude(pk=exclude.pk)
    return qs.exists()


def place(patient, therapist, weekday, slot_index, appointment=None):
    """환자를 그리드 칸에 배정(신규 생성) 또는 기존 배정을 이동.

    대상 칸이 다른 배정으로 차 있으면 ScheduleConflict.
    배정되면 상태가 `시행중`으로 전환되고, 환자에 담당치료사가 기록된다.
    예약 대기칸에 있던 환자는 자동으로 그 칸에서 빠진다.
    """
    if _occupied(therapist, weekday, slot_index, exclude=appointment):
        raise ScheduleConflict('이미 배정된 시간대입니다.')

    if appointment is not None:
        appointment.therapist = therapist
        appointment.weekday = weekday
        appointment.slot_index = slot_index
        appointment.save()
    else:
        appointment = Appointment.objects.create(
            patient=patient, therapist=therapist,
            weekday=weekday, slot_index=slot_index)

    # 예약 대기칸에 있었으면 비운다(이제 실제 시간표에 배정됨).
    Reservation.objects.filter(patient=patient).delete()

    fields = []
    if patient.therapist_id != therapist.id:
        patient.therapist = therapist
        fields.append('therapist')
    if patient.status != Status.DONE and patient.status != Status.ONGOING:
        patient.status = Status.ONGOING
        fields.append('status')
    if fields:
        fields.append('updated_at')
        patient.save(update_fields=fields)
    return appointment


def unassign(appointment):
    """그리드에서 배정 제거. 남은 배정도 회차 기록도 없으면 대기중으로 되돌림."""
    patient = appointment.patient
    appointment.delete()
    if (patient.status != Status.WAITING
            and not patient.appointments.exists()
            and patient.session_count == 0):
        patient.status = Status.WAITING
        patient.save(update_fields=['status', 'updated_at'])


def reserve(patient, weekday, period):
    """예약 대기칸(요일×오전/오후)에 환자를 등록/이동. 상태를 예약완료로 전환."""
    order = Reservation.objects.filter(weekday=weekday, period=period).count()
    reservation, _ = Reservation.objects.update_or_create(
        patient=patient,
        defaults={'weekday': weekday, 'period': period, 'order': order},
    )
    if patient.status == Status.WAITING:
        patient.status = Status.BOOKED
        patient.save(update_fields=['status', 'updated_at'])
    return reservation


def unreserve(patient):
    """예약 대기칸에서 환자를 빼낸다. 배정도 없으면 대기중으로 되돌림."""
    Reservation.objects.filter(patient=patient).delete()
    if patient.status == Status.BOOKED and not patient.appointments.exists():
        patient.status = Status.WAITING
        patient.save(update_fields=['status', 'updated_at'])


def toggle_fixed(appointment):
    appointment.is_fixed = not appointment.is_fixed
    appointment.save(update_fields=['is_fixed'])
    return appointment.is_fixed
