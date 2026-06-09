from django.db import models


# 기본 시간대: 40분 단위 하루 10타임 (오전 4 + 오후 6)
DEFAULT_TIME_SLOTS = [
    {'start': '09:00', 'end': '09:40'},
    {'start': '09:40', 'end': '10:20'},
    {'start': '10:20', 'end': '11:00'},
    {'start': '11:00', 'end': '11:40'},
    {'start': '13:00', 'end': '13:40'},
    {'start': '13:40', 'end': '14:20'},
    {'start': '14:20', 'end': '15:00'},
    {'start': '15:00', 'end': '15:40'},
    {'start': '15:40', 'end': '16:20'},
    {'start': '16:20', 'end': '17:00'},
]


class Weekday(models.IntegerChoices):
    MON = 0, '월'
    TUE = 1, '화'
    WED = 2, '수'
    THU = 3, '목'
    FRI = 4, '금'


class Period(models.IntegerChoices):
    """예약 대기칸 구분: 오전/오후."""
    AM = 0, '오전'
    PM = 1, '오후'


# 도수치료 전 선행치료(기본물리/단순재활) 최소 요건: 2주 이상 + 4회 이상
PRELIM_REQUIRED = 4


class Category(models.TextChoices):
    """부위/단계 분류(v2). 처방코드 단일화에 따라 등록 시 이 분류를 선택한다."""
    LUMBAR1 = 'lumbar1', 'Lumbar phase1'
    LUMBAR2 = 'lumbar2', 'Lumbar phase2'
    LUMBAR3 = 'lumbar3', 'Lumbar phase3'
    CERVICAL = 'cervical', 'Cervical'
    SHOULDER1 = 'shoulder1', 'Shoulder phase1'
    SHOULDER2 = 'shoulder2', 'Shoulder phase2'
    SHOULDER3 = 'shoulder3', 'Shoulder phase3'
    ETC = 'etc', '기타'


class Status(models.TextChoices):
    WAITING = '대기중', '대기중'
    BOOKED = '예약완료', '예약완료'
    ONGOING = '시행중', '시행중'
    DONE = '종결', '종결'


class Sex(models.TextChoices):
    F = 'F', 'F'
    M = 'M', 'M'
    O = 'O', 'O'


class PrescriptionCode(models.TextChoices):
    SIMPLE = '간단', '도수치료 간단'
    BASIC = '기본', '도수치료 기본'
    COMPLEX = '복잡', '도수치료 복잡'


class Therapist(models.Model):
    """도수치료사."""
    name = models.CharField('이름', max_length=50, unique=True)
    is_active = models.BooleanField('활성', default=True)
    order = models.IntegerField('정렬', default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Patient(models.Model):
    """환자(= 처방 단위). 상태 흐름: 대기중 → 예약완료 → 시행중 → 종결."""
    registration_number = models.CharField('등록번호', max_length=20, db_index=True)
    name = models.CharField('성명', max_length=50, db_index=True)
    age = models.IntegerField('나이', null=True, blank=True)
    sex = models.CharField('성별', max_length=1, choices=Sex.choices, blank=True)

    prescription_date = models.DateField('처방일자', null=True, blank=True)
    prescription_code = models.CharField(
        '처방코드', max_length=4, choices=PrescriptionCode.choices,
        default=PrescriptionCode.SIMPLE,
    )
    # v2: 부위/단계 분류(처방코드 단일화). '기타'면 category_etc에 자유 입력.
    category = models.CharField('부위/단계', max_length=10, choices=Category.choices, blank=True)
    category_etc = models.CharField('부위/단계(기타)', max_length=100, blank=True)
    is_outpatient = models.BooleanField('외래(외)', default=True)
    memo = models.CharField('환자 메모', max_length=255, blank=True)  # 부위/상병
    department = models.CharField('진료과', max_length=50, default='재활의학과', blank=True)

    therapist = models.ForeignKey(
        Therapist, verbose_name='담당치료사', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='patients',
    )
    status = models.CharField(
        '상태', max_length=4, choices=Status.choices,
        default=Status.WAITING, db_index=True,
    )

    phone = models.CharField('연락처', max_length=30, blank=True)
    preferred_days = models.CharField('희망요일', max_length=50, blank=True)
    preferred_times = models.CharField('희망시간', max_length=50, blank=True)
    note = models.TextField('비고', blank=True)
    last_contact_date = models.DateField('마지막연락일', null=True, blank=True)
    contact_result = models.CharField('연락결과', max_length=255, blank=True)

    target_sessions = models.IntegerField('종결 목표 회차', default=6)
    completion_eval_date = models.DateField('종결평가 예정일', null=True, blank=True)
    start_date = models.DateField('도수 시작일', null=True, blank=True)
    end_date = models.DateField('도수 종결일', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-prescription_date', 'name']

    def __str__(self):
        return f'{self.name} ({self.registration_number})'

    @property
    def session_count(self):
        return self.sessions.count()

    @property
    def category_label(self):
        """부위/단계 표시값. 기타면 직접 입력값, 미지정이면 빈 문자열."""
        if self.category == Category.ETC:
            return self.category_etc or '기타'
        if self.category:
            return self.get_category_display()
        return ''

    @property
    def is_completion_due(self):
        """종결 목표 회차 도달(미종결 상태)이면 종결평가 대상."""
        return self.status != Status.DONE and self.session_count >= self.target_sessions

    @property
    def prelim_count(self):
        return self.prelim_sessions.count()

    @property
    def is_prelim_done(self):
        """선행치료 요건(기본물리/단순재활 최소 4회) 충족 → 도수치료 전환 가능."""
        return self.prelim_count >= PRELIM_REQUIRED


class Appointment(models.Model):
    """주간 시간표의 한 칸 배정(요일×시간대). 매주 반복."""
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name='appointments',
    )
    therapist = models.ForeignKey(
        Therapist, on_delete=models.CASCADE, related_name='appointments',
    )
    weekday = models.IntegerField('요일', choices=Weekday.choices)
    slot_index = models.IntegerField('시간대 인덱스')  # 0..9
    is_fixed = models.BooleanField('스케줄 고정', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 한 치료사의 같은 요일·시간대 칸은 하나의 배정만 허용(충돌 방지)
        constraints = [
            models.UniqueConstraint(
                fields=['therapist', 'weekday', 'slot_index'],
                name='unique_slot_per_therapist',
            )
        ]
        ordering = ['weekday', 'slot_index']

    def __str__(self):
        return f'{self.get_weekday_display()} {self.slot_index} - {self.patient.name}'


class Reservation(models.Model):
    """예약 대기칸: 요일(월~금)×오전/오후 별 '다음 차례' 대기열.

    주간 시간표가 가득 찬 상황에서, 해당 요일·시간대에 자리가 나면
    다음으로 시작할 환자를 순번대로 모아둔다. 치료사는 구분하지 않는다.
    한 환자는 한 칸에만 존재한다(OneToOne).
    """
    patient = models.OneToOneField(
        Patient, on_delete=models.CASCADE, related_name='reservation',
    )
    weekday = models.IntegerField('요일', choices=Weekday.choices)
    period = models.IntegerField('시간대', choices=Period.choices)
    order = models.IntegerField('순번', default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['weekday', 'period', 'order', 'created_at']

    def __str__(self):
        return f'{self.get_weekday_display()} {self.get_period_display()} - {self.patient.name}'


class Session(models.Model):
    """도수치료 회차 실시 기록."""
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name='sessions',
    )
    date = models.DateField('실시일')
    number = models.IntegerField('회차')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['number']

    def __str__(self):
        return f'{self.patient.name} {self.number}회'


class PrelimSession(models.Model):
    """선행치료(기본물리치료/단순재활치료) 실시 기록.

    도수치료 관리급여 전환 전 '2주 이상·4회 이상' 선행치료 요건을 추적한다.
    도수치료 회차(Session)와 별개로 카운트한다.
    """
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name='prelim_sessions',
    )
    date = models.DateField('실시일')
    number = models.IntegerField('회차')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['number']

    def __str__(self):
        return f'{self.patient.name} 선행 {self.number}회'


class Settings(models.Model):
    """앱 전역 설정(싱글톤). 시간대 구성 등."""
    time_slots = models.JSONField('시간대 구성', default=list)

    class Meta:
        verbose_name = '설정'
        verbose_name_plural = '설정'

    def save(self, *args, **kwargs):
        self.pk = 1  # 싱글톤 강제
        if not self.time_slots:
            self.time_slots = DEFAULT_TIME_SLOTS
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'time_slots': DEFAULT_TIME_SLOTS})
        return obj
