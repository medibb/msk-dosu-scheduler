from django.test import TestCase, override_settings
from django.urls import reverse

from scheduler.models import Patient, Status, Therapist


@override_settings(APP_PASSWORD='pw')
class PatientViewTests(TestCase):
    def setUp(self):
        self.client.post(reverse('login'), {'password': 'pw'})
        self.t = Therapist.objects.get(name='최수홍')
        self.p1 = Patient.objects.create(
            registration_number='100', name='홍길동', status=Status.WAITING, therapist=self.t)
        self.p2 = Patient.objects.create(
            registration_number='200', name='김철수', status=Status.ONGOING)

    def test_waitlist_lists_all(self):
        resp = self.client.get(reverse('waitlist'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '홍길동')
        self.assertContains(resp, '김철수')

    def test_waitlist_filter_by_status(self):
        resp = self.client.get(reverse('waitlist'), {'status': Status.WAITING})
        self.assertContains(resp, '홍길동')
        self.assertNotContains(resp, '김철수')

    def test_waitlist_search_by_name(self):
        resp = self.client.get(reverse('waitlist'), {'q': '철수'})
        self.assertContains(resp, '김철수')
        self.assertNotContains(resp, '홍길동')

    def test_waitlist_filter_by_therapist(self):
        resp = self.client.get(reverse('waitlist'), {'therapist': self.t.id})
        self.assertContains(resp, '홍길동')
        self.assertNotContains(resp, '김철수')

    def test_create_patient(self):
        resp = self.client.post(reverse('patient_create'), {
            'registration_number': '300', 'name': '이영희',
            'prescription_code': '간단', 'status': Status.WAITING,
            'department': '재활의학과', 'target_sessions': 6,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Patient.objects.filter(name='이영희').exists())

    def test_status_transition_advances_one_step(self):
        self.client.post(reverse('patient_set_status', args=[self.p1.pk]))
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.status, Status.BOOKED)

    def test_status_to_done_sets_end_date(self):
        self.client.post(reverse('patient_set_status', args=[self.p2.pk]),
                         {'status': Status.DONE})
        self.p2.refresh_from_db()
        self.assertEqual(self.p2.status, Status.DONE)
        self.assertIsNotNone(self.p2.end_date)
