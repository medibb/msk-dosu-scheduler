import json

from django.test import TestCase, override_settings
from django.urls import reverse

from scheduler.models import Appointment, Patient, Status, Therapist
from scheduler.services import schedule as sch


class ScheduleServiceTests(TestCase):
    def setUp(self):
        self.t = Therapist.objects.get(name='최수홍')
        self.t2 = Therapist.objects.get(name='김대현')
        self.p1 = Patient.objects.create(
            registration_number='1', name='가환자', status=Status.WAITING)
        self.p2 = Patient.objects.create(
            registration_number='2', name='나환자', status=Status.WAITING)

    def test_place_creates_appointment_and_books_patient(self):
        appt = sch.place(self.p1, self.t, weekday=0, slot_index=0)
        self.assertIsNotNone(appt.pk)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.status, Status.BOOKED)

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
