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
        # v2: 처방코드/상태/진료과/담당치료사 입력 없이 부위/단계(category)로 등록
        resp = self.client.post(reverse('patient_create'), {
            'registration_number': '300', 'name': '이영희',
            'category': 'lumbar1', 'target_sessions': 6,
        })
        self.assertEqual(resp.status_code, 302)
        p = Patient.objects.get(name='이영희')
        self.assertEqual(p.status, Status.WAITING)   # 기본 대기중
        self.assertEqual(p.category, 'lumbar1')

    def test_create_patient_etc_category(self):
        resp = self.client.post(reverse('patient_create'), {
            'registration_number': '301', 'name': '박기타',
            'category': 'etc', 'category_etc': 'Knee 재활', 'target_sessions': 6,
        })
        self.assertEqual(resp.status_code, 302)
        p = Patient.objects.get(name='박기타')
        self.assertEqual(p.category_label, 'Knee 재활')

    def test_waitlist_sort_by_name_asc_desc(self):
        # p1=홍길동, p2=김철수 → 이름 오름차순이면 김철수가 먼저
        asc = self.client.get(reverse('waitlist'), {'sort': 'name', 'dir': 'asc'}).content.decode()
        self.assertLess(asc.index('김철수'), asc.index('홍길동'))
        desc = self.client.get(reverse('waitlist'), {'sort': 'name', 'dir': 'desc'}).content.decode()
        self.assertLess(desc.index('홍길동'), desc.index('김철수'))

    def test_waitlist_sort_links_preserve_filter(self):
        resp = self.client.get(reverse('waitlist'), {'therapist': self.t.id})
        # 정렬 링크에 현재 치료사 필터가 유지되어야 한다
        self.assertContains(resp, f'therapist={self.t.id}')
        self.assertContains(resp, 'sort=name')

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
