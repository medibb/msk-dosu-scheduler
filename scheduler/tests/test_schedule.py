import json

from django.test import TestCase, override_settings
from django.urls import reverse

from scheduler.models import Appointment, Patient, Reservation, Status, Therapist
from scheduler.services import schedule as sch


class ScheduleServiceTests(TestCase):
    def setUp(self):
        self.t = Therapist.objects.get(name='최수홍')
        self.t2 = Therapist.objects.get(name='김대현')
        self.p1 = Patient.objects.create(
            registration_number='1', name='가환자', status=Status.WAITING)
        self.p2 = Patient.objects.create(
            registration_number='2', name='나환자', status=Status.WAITING)

    def test_place_creates_appointment_starts_patient_and_records_therapist(self):
        appt = sch.place(self.p1, self.t, weekday=0, slot_index=0)
        self.assertIsNotNone(appt.pk)
        self.p1.refresh_from_db()
        # v2: 시간표 배정 → 시행중 + 담당치료사 기록
        self.assertEqual(self.p1.status, Status.ONGOING)
        self.assertEqual(self.p1.therapist, self.t)

    def test_place_conflict_when_cell_occupied(self):
        sch.place(self.p1, self.t, 0, 0)
        with self.assertRaises(sch.ScheduleConflict):
            sch.place(self.p2, self.t, 0, 0)

    def test_same_cell_different_therapist_is_ok(self):
        sch.place(self.p1, self.t, 0, 0)
        appt = sch.place(self.p2, self.t2, 0, 0)  # 다른 치료사 → 충돌 아님
        self.assertIsNotNone(appt.pk)

    def test_move_existing_appointment(self):
        appt = sch.place(self.p1, self.t, 0, 0)
        moved = sch.place(self.p1, self.t, weekday=2, slot_index=5, appointment=appt)
        self.assertEqual(moved.pk, appt.pk)
        self.assertEqual(moved.weekday, 2)
        self.assertEqual(moved.slot_index, 5)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_move_into_occupied_cell_conflicts(self):
        a1 = sch.place(self.p1, self.t, 0, 0)
        sch.place(self.p2, self.t, 1, 1)
        with self.assertRaises(sch.ScheduleConflict):
            sch.place(self.p1, self.t, 1, 1, appointment=a1)

    def test_unassign_removes_and_reverts_status(self):
        appt = sch.place(self.p1, self.t, 0, 0)
        sch.unassign(appt)
        self.p1.refresh_from_db()
        self.assertEqual(Appointment.objects.count(), 0)
        self.assertEqual(self.p1.status, Status.WAITING)

    def test_build_grid_shape(self):
        sch.place(self.p1, self.t, 0, 0)
        grid = sch.build_grid(self.t)
        self.assertEqual(len(grid), 10)          # 10 타임
        self.assertEqual(len(grid[0]['cells']), 5)  # 월~금
        self.assertEqual(grid[0]['cells'][0]['appointment'].patient, self.p1)

    def test_toggle_fixed(self):
        appt = sch.place(self.p1, self.t, 0, 0)
        self.assertTrue(sch.toggle_fixed(appt))
        self.assertFalse(sch.toggle_fixed(appt))

    def test_reserve_sets_booked(self):
        sch.reserve(self.p1, weekday=0, period=0)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.status, Status.BOOKED)
        self.assertEqual(Reservation.objects.filter(patient=self.p1).count(), 1)

    def test_reserve_is_single_slot_per_patient(self):
        sch.reserve(self.p1, weekday=0, period=0)
        sch.reserve(self.p1, weekday=2, period=1)  # 다른 칸으로 이동
        self.assertEqual(Reservation.objects.filter(patient=self.p1).count(), 1)
        r = Reservation.objects.get(patient=self.p1)
        self.assertEqual((r.weekday, r.period), (2, 1))

    def test_unreserve_reverts_to_waiting(self):
        sch.reserve(self.p1, 0, 0)
        sch.unreserve(self.p1)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.status, Status.WAITING)
        self.assertFalse(Reservation.objects.filter(patient=self.p1).exists())

    def test_place_clears_reservation(self):
        sch.reserve(self.p1, 0, 0)
        sch.place(self.p1, self.t, 0, 0)
        self.assertFalse(Reservation.objects.filter(patient=self.p1).exists())
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.status, Status.ONGOING)

    def test_build_reservation_grid_shape(self):
        sch.reserve(self.p1, weekday=0, period=0)  # 월 오전
        rows = sch.build_reservation_grid()
        self.assertEqual(len(rows), 2)             # 오전/오후
        self.assertEqual(len(rows[0]['cells']), 5)  # 월~금
        self.assertEqual(rows[0]['cells'][0]['reservations'][0].patient, self.p1)

    def test_build_grid_all_has_cell_per_therapist(self):
        sch.place(self.p1, self.t, 0, 0)
        rows = sch.build_grid_all([self.t, self.t2])
        self.assertEqual(len(rows), 10)
        self.assertEqual(len(rows[0]['cells']), 5 * 2)  # 요일×치료사
        self.assertEqual(rows[0]['cells'][0]['appointment'].patient, self.p1)


@override_settings(APP_PASSWORD='pw')
class ScheduleApiTests(TestCase):
    def setUp(self):
        self.client.post(reverse('login'), {'password': 'pw'})
        self.t = Therapist.objects.get(name='최수홍')
        self.p1 = Patient.objects.create(registration_number='1', name='가환자', status=Status.WAITING)
        self.p2 = Patient.objects.create(registration_number='2', name='나환자', status=Status.WAITING)

    def _post(self, name, payload):
        return self.client.post(reverse(name), data=json.dumps(payload),
                                content_type='application/json')

    def test_schedule_page_renders(self):
        resp = self.client.get(reverse('schedule'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '가환자')  # 대기자에 표시

    def test_api_place_assigns(self):
        resp = self._post('api_place', {
            'patient_id': self.p1.id, 'therapist_id': self.t.id,
            'weekday': 0, 'slot_index': 0})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])
        self.assertEqual(Appointment.objects.count(), 1)

    def test_api_place_conflict_returns_409(self):
        self._post('api_place', {'patient_id': self.p1.id, 'therapist_id': self.t.id,
                                 'weekday': 0, 'slot_index': 0})
        resp = self._post('api_place', {'patient_id': self.p2.id, 'therapist_id': self.t.id,
                                        'weekday': 0, 'slot_index': 0})
        self.assertEqual(resp.status_code, 409)
        self.assertFalse(resp.json()['ok'])

    def test_api_unassign(self):
        appt = sch.place(self.p1, self.t, 0, 0)
        resp = self._post('api_unassign', {'appointment_id': appt.id})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_api_reserve_and_unreserve(self):
        resp = self._post('api_reserve', {
            'patient_id': self.p1.id, 'weekday': 0, 'period': 0})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])
        self.assertEqual(Reservation.objects.filter(patient=self.p1).count(), 1)

        resp = self._post('api_unreserve', {'patient_id': self.p1.id})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Reservation.objects.filter(patient=self.p1).exists())

    def test_schedule_all_view_renders(self):
        sch.place(self.p1, self.t, 0, 0)
        resp = self.client.get(reverse('schedule'))   # 전체 보기(기본)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '전체')
        self.assertContains(resp, '예약 대기')
