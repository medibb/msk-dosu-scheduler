"""통계 집계: 기간 내 도수치료(회차) 건수를 처방코드·치료사·부위별로 집계."""
import csv
import io
from collections import Counter

from ..models import PrescriptionCode, Session

# 부위 분류(환자 메모 기반 키워드 매칭). 표준 양식이 없어 휴리스틱으로 묶는다.
REGION_RULES = [
    ('어깨/견관절', ['어깨', '견관절', '견갑', '회전근', 'shoulder', 'rotator', 'sse']),
    ('허리', ['허리', '요추', '요통', 'lbp', 'lumbar']),
    ('목', ['목', '경추', 'cervical', 'neck']),
    ('무릎', ['무릎', '슬관절', 'knee', 'tka']),
    ('골반/고관절', ['골반', '고관절', 'hip', 'pelvic']),
]


def categorize_region(memo):
    text = (memo or '').lower()
    for label, keywords in REGION_RULES:
        if any(kw in text for kw in keywords):
            return label
    return '기타'


def aggregate(start_date, end_date):
    """[start_date, end_date] 기간에 실시된 회차를 집계."""
    sessions = (Session.objects
                .filter(date__gte=start_date, date__lte=end_date)
                .select_related('patient', 'patient__therapist'))

    by_code = Counter()
    by_therapist = Counter()
    by_region = Counter()
    total = 0
    for s in sessions:
        total += 1
        p = s.patient
        by_code[p.get_prescription_code_display()] += 1
        by_therapist[p.therapist.name if p.therapist else '미지정'] += 1
        by_region[categorize_region(p.memo)] += 1

    def rows(counter):
        return [{'key': k, 'count': c} for k, c in counter.most_common()]

    return {
        'start': start_date,
        'end': end_date,
        'total': total,
        'by_code': rows(by_code),
        'by_therapist': rows(by_therapist),
        'by_region': rows(by_region),
    }


def to_csv(data):
    """집계 결과를 CSV 문자열로."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['구분', '항목', '건수'])
    w.writerow(['기간', f"{data['start']} ~ {data['end']}", data['total']])
    for section, label in [('by_code', '처방코드'), ('by_therapist', '치료사'), ('by_region', '부위')]:
        for row in data[section]:
            w.writerow([label, row['key'], row['count']])
    return buf.getvalue()
