"""엑셀 '근골격계도수치료 처방 명단' 시트 → Patient 임포트.

순수 파싱 함수(행 → dict)와 DB 적재(import_patients)를 분리해 테스트하기 쉽게 한다.
"""
from datetime import date

from ..models import PrescriptionCode, Status

# 시트 컬럼 인덱스 (헤더 행 기준)
COL = {
    'prescription_date': 1,
    'registration_number': 2,
    'name': 3,
    'prescription_code': 4,
    'memo': 5,
    'department': 6,
    'age': 7,
    'sex': 8,
    'therapist': 9,
    'status': 10,
    'note': 11,
    'phone': 12,
    'preferred_days': 13,
    'preferred_times': 14,
}

STATUS_MAP = {
    '대기중': Status.WAITING,
    '예약완료': Status.BOOKED,
    '시행중': Status.ONGOING,
    '종결': Status.DONE,
}

CODE_MAP = {
    '간단': PrescriptionCode.SIMPLE,
    '기본': PrescriptionCode.BASIC,
    '복잡': PrescriptionCode.COMPLEX,
}


def _s(v):
    """셀 값을 정리된 문자열로."""
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def parse_prescription_code(raw):
    """'도수치료 간단 외 ' → ('간단', True). 외래(외) 포함 여부도 반환."""
    text = _s(raw)
    is_outpatient = '외' in text
    for key, code in CODE_MAP.items():
        if key in text:
            return code, is_outpatient
    return PrescriptionCode.SIMPLE, is_outpatient


def parse_age(raw):
    """'74y' / 74 / '74' → 74. 파싱 불가 시 None."""
    text = _s(raw)
    digits = ''.join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


def parse_excel_date(raw):
    """20250502 또는 '20250502' → date(2025,5,2). date 객체면 그대로. 실패 시 None."""
    if isinstance(raw, date):
        return raw
    text = _s(raw)
    digits = ''.join(ch for ch in text if ch.isdigit())
    if len(digits) == 8:
        try:
            return date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
        except ValueError:
            return None
    return None


def parse_status(raw):
    return STATUS_MAP.get(_s(raw), Status.WAITING)


def parse_therapist_name(raw):
    """'최수홍,김대현' → '최수홍' (첫 담당자). 비정상 값은 빈 문자열."""
    text = _s(raw)
    if not text:
        return ''
    first = text.split(',')[0].strip()
    # '연락x 9/1', '오후3시30 가능시' 같은 메모성 값 거르기
    if len(first) > 5 or any(ch.isdigit() for ch in first):
        return ''
    return first


def parse_row(row):
    """시트 한 행(튜플) → Patient 필드 dict. 성명이 없으면 None."""
    def cell(key):
        idx = COL[key]
        return row[idx] if idx < len(row) else None

    name = _s(cell('name'))
    if not name:
        return None

    code, is_outpatient = parse_prescription_code(cell('prescription_code'))
    return {
        'registration_number': _s(cell('registration_number')),
        'name': name,
        'age': parse_age(cell('age')),
        'sex': _s(cell('sex'))[:1],
        'prescription_date': parse_excel_date(cell('prescription_date')),
        'prescription_code': code,
        'is_outpatient': is_outpatient,
        'memo': _s(cell('memo'))[:255],
        'department': _s(cell('department')) or '재활의학과',
        'therapist_name': parse_therapist_name(cell('therapist')),
        'status': parse_status(cell('status')),
        'note': _s(cell('note')),
        'phone': _s(cell('phone')),
        'preferred_days': _s(cell('preferred_days')),
        'preferred_times': _s(cell('preferred_times')),
    }


def parse_rows(rows):
    """행 목록(헤더 포함) → 유효 환자 dict 목록. 첫 행은 헤더로 건너뛴다."""
    result = []
    for row in rows[1:]:
        parsed = parse_row(row)
        if parsed:
            result.append(parsed)
    return result


def load_rows(file_or_path, sheet_name='근골격계도수치료 처방 명단'):
    """엑셀 파일에서 지정 시트의 모든 행을 튜플 목록으로 읽는다."""
    import openpyxl
    wb = openpyxl.load_workbook(file_or_path, read_only=True, data_only=True)
    ws = wb[sheet_name]
    return list(ws.iter_rows(values_only=True))


def import_patients(file_or_path, sheet_name='근골격계도수치료 처방 명단'):
    """엑셀 → Patient 일괄 생성. (등록번호+성명) 중복은 건너뛴다."""
    from ..models import Patient, Therapist

    rows = load_rows(file_or_path, sheet_name)
    parsed = parse_rows(rows)

    created, skipped = 0, 0
    therapist_cache = {t.name: t for t in Therapist.objects.all()}
    for data in parsed:
        tname = data.pop('therapist_name')
        therapist = None
        if tname:
            therapist = therapist_cache.get(tname)
            if therapist is None:
                therapist = Therapist.objects.create(name=tname, order=99)
                therapist_cache[tname] = therapist

        exists = Patient.objects.filter(
            registration_number=data['registration_number'],
            name=data['name'],
        ).exists()
        if exists:
            skipped += 1
            continue
        Patient.objects.create(therapist=therapist, **data)
        created += 1

    return {'created': created, 'skipped': skipped, 'total': len(parsed)}
