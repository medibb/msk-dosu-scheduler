from datetime import date

from django.test import TestCase

from scheduler.models import Patient, PrescriptionCode, Status, Therapist
from scheduler.services import import_excel as ie


class ParseHelperTests(TestCase):
    def test_parse_prescription_code(self):
        self.assertEqual(ie.parse_prescription_code('도수치료 간단 외 '),
                         (PrescriptionCode.SIMPLE, True))
        self.assertEqual(ie.parse_prescription_code('도수치료 기본'),
                         (PrescriptionCode.BASIC, False))
        self.assertEqual(ie.parse_prescription_code('도수치료 복잡 외'),
                         (PrescriptionCode.COMPLEX, True))

    def test_parse_age(self):
        self.assertEqual(ie.parse_age('74y'), 74)
        self.assertEqual(ie.parse_age(54.0), 54)
        self.assertIsNone(ie.parse_age(None))
        self.assertIsNone(ie.parse_age(''))

    def test_parse_excel_date(self):
        self.assertEqual(ie.parse_excel_date(20250502.0), date(2025, 5, 2))
        self.assertEqual(ie.parse_excel_date('20250502'), date(2025, 5, 2))
        self.assertEqual(ie.parse_excel_date(date(2025, 5, 2)), date(2025, 5, 2))
        self.assertIsNone(ie.parse_excel_date('bad'))

    def test_parse_status(self):
        self.assertEqual(ie.parse_status('시행중'), Status.ONGOING)
        self.assertEqual(ie.parse_status('종결'), Status.DONE)
        # 알 수 없는 값은 대기중으로
        self.assertEqual(ie.parse_status('재활의학과'), Status.WAITING)

    def test_parse_therapist_name(self):
        self.assertEqual(ie.parse_therapist_name('최수홍'), '최수홍')
        self.assertEqual(ie.parse_therapist_name('최수홍,김대현'), '최수홍')
        # 메모성 비정상 값은 거른다
        self.assertEqual(ie.parse_therapist_name('연락x 9/1'), '')
        self.assertEqual(ie.parse_therapist_name('오후3시30 가능시'), '')


# 헤더 + 데이터 행 (실제 시트 컬럼 순서 모사)
HEADER = ('marker', '처방일자', '등록번호', '성명', '처방코드', '환자 메모',
          '진료과', '나이', '성별', '담당치료사', '상태', '비고', '연락처',
          '희망요일', '희망시간')
ROW1 = (None, 20250502.0, '210357213', '김계선', '도수치료 기본 외 ', '견관절',
        '재활의학과', '74y', 'F', '최수홍', '종결', '메모', '010-1111-2222',
        '월,수', '오전')
ROW_EMPTY = (None, 20250502.0, '999', None, '도수치료 간단', '', '재활의학과',
             None, '', '', '대기중', '', '', '', '')


class ParseRowTests(TestCase):
    def test_parse_row_maps_fields(self):
        d = ie.parse_row(ROW1)
        self.assertEqual(d['registration_number'], '210357213')
        self.assertEqual(d['name'], '김계선')
        self.assertEqual(d['age'], 74)
        self.assertEqual(d['sex'], 'F')
        self.assertEqual(d['prescription_date'], date(2025, 5, 2))
        self.assertEqual(d['prescription_code'], PrescriptionCode.BASIC)
        self.assertTrue(d['is_outpatient'])
        self.assertEqual(d['memo'], '견관절')
        self.assertEqual(d['therapist_name'], '최수홍')
        self.assertEqual(d['status'], Status.DONE)

    def test_parse_row_skips_nameless(self):
        self.assertIsNone(ie.parse_row(ROW_EMPTY))

    def test_parse_rows_skips_header_and_empty(self):
        rows = [HEADER, ROW1, ROW_EMPTY]
        result = ie.parse_rows(rows)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], '김계선')


class ImportPatientsTests(TestCase):
    # 치료사 '최수홍'은 시드 마이그레이션(0002)으로 이미 존재한다.

    def test_import_creates_patients_and_links_therapist(self):
        # load_rows 를 모킹하지 않고, parse 결과를 직접 적재하는 경로를 검증
        rows = [HEADER, ROW1]
        import unittest.mock as mock
        with mock.patch.object(ie, 'load_rows', return_value=rows):
            stats = ie.import_patients('dummy.xlsx')
        self.assertEqual(stats['created'], 1)
        p = Patient.objects.get(registration_number='210357213')
        self.assertEqual(p.name, '김계선')
        self.assertEqual(p.therapist.name, '최수홍')

    def test_import_skips_duplicates(self):
        rows = [HEADER, ROW1, ROW1]
        import unittest.mock as mock
        with mock.patch.object(ie, 'load_rows', return_value=rows):
            stats = ie.import_patients('dummy.xlsx')
        self.assertEqual(stats['created'], 1)
        self.assertEqual(stats['skipped'], 1)
