# Tasks: 근골격계 도수치료 스케줄링 웹앱

PRD: `tasks/prd-msk-dosu-scheduling.md`

## Relevant Files

- `package.json` - 의존성 및 스크립트(Next.js, Supabase, dnd-kit, SheetJS).
- `next.config.js` - Next.js 설정.
- `.env.local` - Supabase URL/Key, 공용 로그인 비밀번호 (gitignore됨).
- `lib/supabaseClient.ts` - Supabase 클라이언트 초기화.
- `lib/types.ts` - 공용 타입(Patient, Appointment, Therapist, Settings, Status enum).
- `supabase/schema.sql` - DB 테이블 정의(patient, appointment, therapist, settings).
- `lib/auth.ts` - 공용 1계정 로그인/세션 검증 로직.
- `lib/auth.test.ts` - 로그인 로직 단위 테스트.
- `middleware.ts` - 미인증 접근 차단(로그인 페이지로 리다이렉트).
- `app/login/page.tsx` - 로그인 화면.
- `app/layout.tsx` - 전체 레이아웃/네비게이션.
- `app/page.tsx` - 메인(주간 시간표 + 대기자 패널).
- `lib/patients.ts` - 환자 CRUD/상태변경 데이터 액세스.
- `lib/patients.test.ts` - 환자 데이터 로직 단위 테스트.
- `components/PatientForm.tsx` - 환자 등록/수정 폼.
- `components/WaitlistPanel.tsx` - 대기자 목록(필터/검색/드래그 소스).
- `components/PatientCard.tsx` - 환자 카드(이름·회차·부위 요약, 상태 색상).
- `components/PatientDetail.tsx` - 환자 상세/회차 패널.
- `lib/importExcel.ts` - 엑셀 `근골격계도수치료 처방 명단` 시트 파서.
- `lib/importExcel.test.ts` - 엑셀 임포트 매핑 단위 테스트.
- `app/import/page.tsx` - 엑셀 1회 임포트 화면.
- `components/ScheduleGrid.tsx` - 요일×10타임 그리드(드래그앤드롭 배정).
- `components/ScheduleCell.tsx` - 그리드 셀(드롭 타깃).
- `lib/schedule.ts` - 배정/이동/시간대 구성 로직.
- `lib/schedule.test.ts` - 스케줄 로직 단위 테스트.
- `lib/sessions.ts` - 회차 증가/종결평가 알림/종결 처리 로직.
- `lib/sessions.test.ts` - 회차 로직 단위 테스트.
- `app/stats/page.tsx` - 통계 화면.
- `lib/stats.ts` - 기간·코드·부위·치료사별 집계 + CSV 생성.
- `lib/stats.test.ts` - 통계 집계 단위 테스트.

### Notes

- 단위 테스트는 대상 파일과 같은 디렉터리에 둔다(예: `lib/schedule.ts` ↔ `lib/schedule.test.ts`).
- 테스트 실행: `npx jest [경로]` (경로 생략 시 전체 실행).
- 개발 중 저장소는 **public**, 실제 환자 데이터 사용 시 **private**으로 전환.
- 데이터 소스: `../림프 도수치료 2026.xlsx` 의 `근골격계도수치료 처방 명단` 시트.

## Tasks

- [x] 0.0 프로젝트 초기화 및 기능 브랜치 생성
  - [x] 0.1 `exdev/msk-scheduler/`에 git 저장소 초기화 및 초기 커밋(완료)
  - [x] 0.2 기능 브랜치 생성 및 체크아웃 (`git checkout -b feature/msk-dosu-scheduling`)
  - [x] 0.3 GitHub public 원격 저장소 연결 및 push (`medibb/msk-dosu-scheduler`)

- [ ] 1.0 프로젝트 기반 구축 (Next.js + Supabase, 공용 로그인, DB 스키마)
  - [ ] 1.1 Next.js(App Router, TypeScript) 프로젝트 생성 및 기본 의존성 설치
  - [ ] 1.2 Jest + Testing Library 설정(테스트 실행 환경)
  - [ ] 1.3 Supabase 프로젝트 생성, `.env.local`에 URL/Key 설정, `lib/supabaseClient.ts` 작성
  - [ ] 1.4 DB 스키마 작성(`supabase/schema.sql`): `patient`, `appointment`, `therapist`, `settings` 테이블 및 상태 enum(대기중/예약완료/시행중/종결)
  - [ ] 1.5 공용 타입 정의(`lib/types.ts`)
  - [ ] 1.6 공용 1계정 로그인 구현(`lib/auth.ts`, `app/login/page.tsx`, `middleware.ts`) + 테스트
  - [ ] 1.7 기본 레이아웃/네비게이션(`app/layout.tsx`): 시간표 / 대기자 / 통계 / 임포트 메뉴

- [ ] 2.0 환자/대기자 관리 (등록·수정·검색·필터, 상태 흐름, 엑셀 임포트)
  - [ ] 2.1 환자 데이터 액세스 계층(`lib/patients.ts`): 생성/조회/수정/상태변경 + 테스트
  - [ ] 2.2 환자 등록/수정 폼(`components/PatientForm.tsx`): 처방일자·등록번호·성명·처방코드(간단/기본/복잡 + 외 토글)·메모·진료과·나이·성별·담당치료사·연락처·희망요일/시간·비고
  - [ ] 2.3 대기자 패널(`components/WaitlistPanel.tsx`): 상태/치료사/처방일자 필터·정렬, 등록번호·성명 검색
  - [ ] 2.4 환자 카드/상세(`PatientCard.tsx`, `PatientDetail.tsx`): 상태 색상 구분, 마지막연락일·연락결과 기록
  - [ ] 2.5 상태 흐름(대기중→예약완료→시행중→종결) 1~2클릭 전환 구현
  - [ ] 2.6 엑셀 임포트 파서(`lib/importExcel.ts`): `근골격계도수치료 처방 명단` 컬럼 매핑 + 테스트
  - [ ] 2.7 임포트 화면(`app/import/page.tsx`): 파일 업로드 → 미리보기 → 1회 일괄 등록

- [ ] 3.0 주간 시간표 그리드 (10타임 요일×시간 그리드, 드래그앤드롭 배정, 치료사별 보기)
  - [ ] 3.1 시간대 구성 로직(`lib/schedule.ts`): 기본 40분 10타임(09:00~11:40, 13:00~17:00), 설정에서 변경 가능 + 테스트
  - [ ] 3.2 그리드 렌더링(`ScheduleGrid.tsx`, `ScheduleCell.tsx`): 요일(월~금)×10타임
  - [ ] 3.3 dnd-kit로 대기/예약 환자를 빈 셀에 드래그앤드롭 배정 → 상태 자동 전환
  - [ ] 3.4 배정 환자 셀 간 이동(일정 변경) 구현
  - [ ] 3.5 치료사별 보기 전환 / 전체 보기, "스케줄 고정"(매주 반복) 표시
  - [ ] 3.6 배정/이동 시 충돌(같은 시간 중복) 방지 검증 + 테스트

- [ ] 4.0 회차/진행 추적 (회차 증가, 종결 목표(기본 6회) 알림, 종결 처리)
  - [ ] 4.1 회차 데이터 로직(`lib/sessions.ts`): 회차 +1, 실시 날짜 기록 + 테스트
  - [ ] 4.2 환자별 종결 목표 회차(기본 6회, 변경 가능) 설정
  - [ ] 4.3 목표 회차 도달 시 종결평가 예정 알림 표시, 종결평가 예정일 지정/표시
  - [ ] 4.4 상태 `종결` 전환 시 종결일 자동 기록
  - [ ] 4.5 환자 카드/상세에 회차 요약(예: 6회차/6) 노출

- [ ] 5.0 통계/리포트 (기간·처방코드·부위·치료사별 집계, CSV 내보내기)
  - [ ] 5.1 집계 로직(`lib/stats.ts`): 기간(월/분기/연) 총 건수, 처방코드별·부위별·치료사별 + 테스트
  - [ ] 5.2 통계 화면(`app/stats/page.tsx`): 기간 선택 + 집계 표 표시
  - [ ] 5.3 CSV(또는 엑셀) 내보내기
  - [ ] 5.4 최종 점검: 전체 흐름(임포트→대기→배정→회차→종결→통계) E2E 수동 검증
