# Tasks: 근골격계 도수치료 스케줄링 웹앱

PRD: `tasks/prd-msk-dosu-scheduling.md`
스택: **Django 5.2 + SQLite + Docker** (spineview와 동일 패턴)

## Relevant Files

- `requirements.txt` - Python 의존성(Django, dj-database-url, openpyxl).
- `Dockerfile` - 앱 이미지 빌드.
- `docker-compose.yml` - web 서비스 + SQLite 영구 볼륨 마운트.
- `.env` - SECRET_KEY, 공용 로그인 비밀번호, DATABASE_URL (gitignore됨).
- `manage.py` - Django 관리 커맨드.
- `config/settings.py` - Django 설정(DB, 앱 등록, 인증).
- `config/urls.py` - 루트 URL 라우팅.
- `scheduler/models.py` - 핵심 모델(Patient, Appointment, Session, Therapist, Settings).
- `scheduler/admin.py` - Django admin 등록(빠른 데이터 확인용).
- `scheduler/views.py` - 화면/액션 뷰(시간표, 대기자, 통계, 임포트).
- `scheduler/urls.py` - 앱 URL 라우팅.
- `scheduler/forms.py` - 환자 등록/수정 폼.
- `scheduler/auth.py` - 공용 1계정 로그인/세션 검증.
- `scheduler/services/schedule.py` - 시간대 구성·배정·이동·충돌검사 로직.
- `scheduler/services/sessions.py` - 회차 증가·종결평가 알림·종결 처리 로직.
- `scheduler/services/stats.py` - 기간·코드·부위·치료사별 집계 + CSV.
- `scheduler/services/import_excel.py` - `근골격계도수치료 처방 명단` 시트 파서.
- `scheduler/templates/base.html` - 공통 레이아웃/네비게이션.
- `scheduler/templates/schedule.html` - 주간 시간표 그리드(SortableJS DnD).
- `scheduler/templates/waitlist.html` - 대기자 패널.
- `scheduler/templates/stats.html` - 통계 화면.
- `scheduler/templates/import.html` - 엑셀 임포트 화면.
- `scheduler/static/js/schedule.js` - SortableJS 드래그앤드롭 + 배정 AJAX.
- `scheduler/tests/test_schedule.py` - 스케줄 로직 테스트.
- `scheduler/tests/test_sessions.py` - 회차 로직 테스트.
- `scheduler/tests/test_stats.py` - 통계 집계 테스트.
- `scheduler/tests/test_import_excel.py` - 임포트 매핑 테스트.
- `scheduler/tests/test_auth.py` - 로그인 테스트.

### Notes

- 테스트는 `scheduler/tests/`에 두고 `python manage.py test` 로 실행(또는 Docker: `docker compose run --rm web python manage.py test`).
- SQLite 파일(`db.sqlite3`)은 docker-compose 볼륨에 마운트 → 컨테이너 재시작에도 데이터 유지, 모든 기기가 같은 서버에 접속해 공유.
- 개발 중 저장소는 **public**, 실제 환자 데이터 사용 시 **private** 전환. `db.sqlite3`·`.env`는 gitignore.
- 데이터 소스: `../림프 도수치료 2026.xlsx` 의 `근골격계도수치료 처방 명단` 시트.

## Tasks

- [x] 0.0 프로젝트 초기화 및 기능 브랜치 생성
  - [x] 0.1 `exdev/msk-scheduler/`에 git 저장소 초기화 및 초기 커밋
  - [x] 0.2 기능 브랜치 생성 및 체크아웃 (`feature/msk-dosu-scheduling`)
  - [x] 0.3 GitHub public 원격 저장소 연결 및 push (`medibb/msk-dosu-scheduler`)

- [x] 1.0 프로젝트 기반 구축 (Django + SQLite + Docker, 공용 로그인, 데이터 모델)
  - [x] 1.1 Django 프로젝트 생성(`config` 프로젝트 + `scheduler` 앱), `requirements.txt` 작성
  - [x] 1.2 `Dockerfile` + `docker-compose.yml`(web + SQLite 볼륨), `.env`/`.gitignore` 정리
  - [x] 1.3 `settings.py` 구성(dj-database-url로 SQLite 기본, 앱/정적파일/타임존 ko)
  - [x] 1.4 데이터 모델 작성(`models.py`): Patient, Appointment, Session, Therapist, Settings + 상태 choices(대기중/예약완료/시행중/종결) + 마이그레이션
  - [x] 1.5 `admin.py` 등록(데이터 확인용) 및 시드용 치료사(최수홍/김대현/김예지) 데이터
  - [x] 1.6 공용 1계정 로그인(`auth.py`, 로그인 뷰/템플릿, 로그인 필수 미들웨어/데코레이터) + 테스트
  - [x] 1.7 공통 레이아웃/네비게이션(`base.html`): 시간표 / 대기자 / 통계 / 임포트

- [x] 2.0 환자/대기자 관리 (등록·수정·검색·필터, 상태 흐름, 엑셀 임포트)
  - [x] 2.1 환자 등록/수정 폼·뷰(`forms.py`, `views.py`): 처방일자·등록번호·성명·처방코드(간단/기본/복잡 + 외 토글)·메모·진료과·나이·성별·담당치료사·연락처·희망요일/시간·비고
  - [x] 2.2 대기자 패널(`waitlist.html`): 상태/치료사 필터·정렬, 등록번호·성명 검색
  - [x] 2.3 환자 카드/상세: 상태 색상 구분, 마지막연락일·연락결과 기록
  - [x] 2.4 상태 흐름(대기중→예약완료→시행중→종결) 1~2클릭 전환(액션 뷰), 종결 시 종결일 자동 기록
  - [x] 2.5 엑셀 임포트 파서(`services/import_excel.py`): 컬럼 매핑 + 테스트(실데이터 270건 검증)
  - [x] 2.6 임포트 화면(`import.html`): 파일 업로드 → 1회 일괄 등록(중복 건너뜀). 미리보기는 단일단계로 단순화

- [x] 3.0 주간 시간표 그리드 (10타임 요일×시간, 드래그앤드롭 배정, 치료사별 보기)
  - [x] 3.1 시간대 구성 로직(`services/schedule.py`): 기본 40분 10타임(09:00~11:40, 13:00~17:00), 설정 변경 가능 + 테스트
  - [x] 3.2 그리드 렌더링(`schedule.html`): 요일(월~금)×10타임, 셀에 환자 카드
  - [x] 3.3 드래그앤드롭(`schedule.js`, 네이티브 HTML5) + 배정 AJAX 뷰 → 상태 자동 전환(대기중→예약완료)
  - [x] 3.4 배정 환자 셀 간 이동(일정 변경), 그리드→대기자 복귀(해제)
  - [x] 3.5 치료사별 보기 탭 전환, "스케줄 고정"(더블클릭 토글) 표시
  - [x] 3.6 배정/이동 시 충돌(같은 치료사·같은 시간 중복) 방지(unique 제약 + 409) + 테스트

- [x] 4.0 회차/진행 추적 (회차 증가, 종결 목표(기본 6회) 알림, 종결 처리)
  - [x] 4.1 회차 로직(`services/sessions.py`): 회차 +1, 실시 날짜 기록(Session) + 테스트
  - [x] 4.2 환자별 종결 목표 회차(기본 6회, 변경 가능) 필드/설정(폼)
  - [x] 4.3 목표 회차 도달 시 종결평가 알림(상세 배너 + 대기자 ?due=1 목록), 종결평가 예정일 지정/표시
  - [x] 4.4 상태 `종결` 전환 시 종결일 자동 기록
  - [x] 4.5 환자 카드/상세에 회차 요약(예: 6/6) 노출

- [x] 5.0 통계/리포트 (기간·처방코드·부위·치료사별 집계, CSV 내보내기)
  - [x] 5.1 집계 로직(`services/stats.py`): 기간(월/분기/연) 총 건수, 처방코드별·부위별·치료사별 + 테스트
  - [x] 5.2 통계 화면(`stats.html`): 기간 선택(프리셋+직접) + 집계 표
  - [x] 5.3 CSV 내보내기(utf-8-sig, Excel 한글 호환)
  - [x] 5.4 최종 점검: 전체 흐름(임포트→대기→배정→회차→종결→통계) E2E 스모크 검증 통과

- [x] 6.0 v2 UI 개선 (전체보기·예약대기칸·대기일수, 환자등록 간략화, 상태흐름 개정) — 브랜치 `feature/patients_ui`
  - [x] 6.1 데이터 모델: `Category`(부위/단계 8분류)·`Period`(오전/오후) choices, `Patient.category`/`category_etc` 필드, `Reservation`(예약대기칸: patient OneToOne, weekday, period, order) 모델 + 마이그레이션(0003)
  - [x] 6.2 스케줄 서비스(`services/schedule.py`): 배정 시 상태 `시행중`으로 변경 + 환자에 치료사 기록, `reserve()/unreserve()`(예약완료 전환), `build_grid_all()`(요일×치료사 전체 그리드), `build_reservation_grid()`(요일×오전/오후)
  - [x] 6.3 뷰/URL: `schedule`에 전체/치료사별 보기 분기 + 대기자 대기일수 계산·정렬, `api_reserve`/`api_unreserve` 추가
  - [x] 6.4 환자 폼(`forms.py`): 처방코드/외래/진료과/담당치료사/상태 제거, `category`(+기타 직접입력) 추가
  - [x] 6.5 시간표 템플릿(`schedule.html`): 전체 탭(요일×치료사) + 치료사별 탭, 예약대기칸 블록, 대기자 대기일수 표기
  - [x] 6.6 DnD JS(`schedule.js`): 칸별 치료사 인식(전체보기 대응), 예약대기칸 드롭(reserve)·복귀(unreserve) 처리
  - [x] 6.7 환자 폼/상세/대기자 템플릿: 부위/단계 표시(`category_label`), 기타 입력 토글 JS, 제거된 항목 정리
  - [x] 6.8 테스트 갱신: 배정→시행중, 환자등록(category), 예약대기칸(reserve/unreserve) + 전체 회귀 통과(53개)
