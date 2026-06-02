"""주간 시간표 그리드 로직: 시간대 구성, 배정/이동/해제, 충돌 방지."""
from ..models import Appointment, Settings, Status, Weekday


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


def _occupied(therapist, weekday, slot_index, exclude=None):
    qs = Appointment.objects.filter(
        therapist=therapist, weekday=weekday, slot_index=slot_index)
    if exclude is not None:
        qs = qs.exclude(pk=exclude.pk)
    return qs.exists()


def place(patient, therapist, weekday, slot_index, appointment=None):
    """환자를 그리드 칸에 배정(신규 생성) 또는 기존 배정을 이동.

    대상 칸이 다른 배정으로 차 있으면 ScheduleConflict.
    대기중 환자는 예약완료로 자동 전환.
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

    if patient.status == Status.WAITING:
        patient.status = Status.BOOKED
        patient.save(update_fields=['status', 'updated_at'])
    return appointment


def unassign(appointment):
    """그리드에서 배정 제거. 남은 배정이 없고 예약완료면 대기중으로 되돌림."""
    patient = appointment.patient
    appointment.delete()
    if patient.status == Status.BOOKED and not patient.appointments.exists():
        patient.status = Status.WAITING
        patient.save(update_fields=['status', 'updated_at'])


def toggle_fixed(appointment):
    appointment.is_fixed = not appointment.is_fixed
    appointment.save(update_fields=['is_fixed'])
    return appointment.is_fixed
