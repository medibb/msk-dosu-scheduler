from datetime import date

from django.test import TestCase

from scheduler.models import Patient, Session, Status
from scheduler.services import sessions as svc


class SessionServiceTests(TestCase):
    def setUp(self):
        self.p = Patient.objects.create(
            registration_number='1', name='가환자', status=Status.BOOKED, target_sessions=6)

    def test_add_session_increments_number(self):
        s1 = svc.add_session(self.p, date(2026, 6, 1))
        s2 = svc.add_session(self.p, date(2026, 6, 3))
        self.assertEqual(s1.number, 1)
        self.assertEqual(s2.number, 2)
        self.assertEqual(self.p.session_count, 2)

    def test_first_session_sets_ongoing_and_start_date(self):
        svc.add_session(self.p, date(2026, 6, 1))
        self.p.refresh_from_db()
        self.assertEqual(self.p.status, Status.ONGOING)
        self.assertEqual(self.p.start_date, date(2026, 6, 1))

    def test_remove_last_session(self):
        svc.add_session(self.p)
        svc.add_session(self.p)
        svc.remove_last_session(self.p)
        self.assertEqual(self.p.session_count, 1)

    def test_completion_due_when_target_reached(self):
        self.p.target_sessions = 2
        self.p.save()
        svc.add_session(self.p)
        self.assertFalse(self.p.is_completion_due)
        svc.add_session(self.p)
        self.p.refresh_from_db()
        self.assertTrue(self.p.is_completion_due)
        self.assertIn(self.p, svc.completion_due())

    def test_complete_sets_done_and_end_date(self):
        svc.complete(self.p, date(2026, 6, 30))
        self.p.refresh_from_db()
        self.assertEqual(self.p.status, Status.DONE)
        self.assertEqual(self.p.end_date, date(2026, 6, 30))
        # 종결된 환자는 종결평가 대상이 아니다
        self.assertNotIn(self.p, svc.completion_due())
