# 근골격계(MSK) 도수치료 스케줄링 웹앱

도수치료사를 위한 근골격계 도수치료 환자 스케줄링 웹앱.
대기자 관리 → 예약 배정 → 회차 진행 → 종결 → 통계까지 한 화면에서 처리한다.

- 기획 문서(PRD): [`tasks/prd-msk-dosu-scheduling.md`](tasks/prd-msk-dosu-scheduling.md)
- 작업 목록: [`tasks/tasks-msk-dosu-scheduling.md`](tasks/tasks-msk-dosu-scheduling.md)
- 데이터 소스: `../림프 도수치료 2026.xlsx` 의 `근골격계도수치료 처방 명단` 시트 (1회 임포트용, 저장소에는 미포함)

## 핵심 기능
- 주간 시간표 그리드 (요일×40분 10타임, 드래그앤드롭 배정)
- 대기자 관리 (상태: 대기중 → 예약완료 → 시행중 → 종결)
- 회차/진행 추적 (기본 6회 종결, 종결평가 알림)
- 기간·처방코드·부위·치료사별 통계 / CSV 내보내기
- 클라우드 저장(여러 기기 공유), 공용 1계정 로그인

## 기술 스택
- **Django 5.2 + SQLite + Docker** 자체배포 (기존 `spineview`와 동일 패턴)
- 드래그앤드롭: SortableJS · 엑셀 임포트: openpyxl
- 멀티기기 공유: 단일 서버가 `db.sqlite3`(영구 볼륨)를 보유, 모든 기기가 접속해 공유
- 확장: `dj-database-url`로 추후 Postgres 전환 가능 · 클라우드 배포는 Railway/Render/Fly(Docker) (Vercel 비대상)

## 실행 (개발)
```bash
docker compose up --build      # http://localhost:8000
```
