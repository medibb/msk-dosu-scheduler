from datetime import date

from django.test import TestCase

from scheduler.models import Patient, PrescriptionCode, Session, Therapist
from scheduler.services import stats


class RegionTests(TestCase):
    def test_categorize_region(self):
        self.assertEqual(stats.categorize_region('견관절 통증'), '어깨/견관절')
        self.assertEqual(stats.categorize_region('LBP'), '허리')
        self.assertEqual(stats.categorize_region('cervical'), '목')
        self.assertEqual(stats.categorize_region('TKA 재활'), '무릎')
        self.assertEqual(stats.categorize_region('알수없음'), '기타')


class AggregateTests(TestCase):
    def setUp(self):
        self.t = Therapist.objects.get(name='최수홍')
        self.p1 = Patient.objects.create(
            registration_number='1', name='가', memo='LBP',
            prescription_code=PrescriptionCode.SIMPLE, therapist=self.t)
        self.p2 = Patient.objects.create(
            registration_number='2', name='나', memo='견관절',
            prescription_code=PrescriptionCode.COMPLEX)
        # 기간 내 회차 3건, 기간 밖 1건
        Session.objects.create(patient=self.p1, number=1, date=date(2026, 6, 1))
        Session.objects.create(patient=self.p1, number=2, date=date(2026, 6, 10))
        Session.objects.create(patient=self.p2, number=1, date=date(2026, 6, 5))
        Session.objects.create(patient=self.p1, number=3, date=date(2026, 7, 1))  # 범위 밖

    def test_total_within_period(self):
        d = stats.aggregate(date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(d['total'], 3)

    def test_by_therapist_counts(self):
        d = stats.aggregate(date(2026, 6, 1), date(2026, 6, 30))
        by_t = {r['key']: r['count'] for r in d['by_therapist']}
        self.assertEqual(by_t['최수홍'], 2)
        self.assertEqual(by_t['미지정'], 1)

    def test_by_region_and_code(self):
        d = stats.aggregate(date(2026, 6, 1), date(2026, 6, 30))
        by_r = {r['key']: r['count'] for r in d['by_region']}
        self.assertEqual(by_r['허리'], 2)
        self.assertEqual(by_r['어깨/견관절'], 1)

    def test_to_csv_contains_header_and_total(self):
        d = stats.aggregate(date(2026, 6, 1), date(2026, 6, 30))
        csv_text = stats.to_csv(d)
        self.assertIn('구분,항목,건수', csv_text)
        self.assertIn('기간', csv_text)


from django.test import override_settings  # noqa: E402
from django.urls import reverse  # noqa: E402


@override_settings(APP_PASSWORD='pw')
class EmrRecordViewTests(TestCase):
    def setUp(self):
        self.client.post(reverse('login'), {'password': 'pw'})

    def test_emr_page_renders_with_presets(self):
        resp = self.client.get(reverse('emr_record'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '선행치료 경과')
        self.assertContains(resp, '사101')      # 옵션 프리셋 포함
        self.assertContains(resp, 'copybtn')     # 복사 버튼
