# CONTRIBUTING.md — 브랜치 · 커밋 · PR 규칙

작업 영역과 허락이 필요한 변경은 [TEAM.md](TEAM.md)를 먼저 읽는다.

## 브랜치
- `main`에는 직접 푸시하지 않는다. 항상 브랜치를 만들어 PR로 합친다.
- 브랜치 이름: `타입/담당-설명` — 예: `feat/be2-report-status`, `fix/be1-upload-error`
- 타입: `feat`(기능), `fix`(버그), `refactor`, `docs`, `chore`(설정 등), `test`
- 브랜치는 짧게 유지한다. 작업 시작 전에 `main`을 최신으로 받는다.

## 커밋 메시지
`타입(도메인): 한글 설명` — 예: `feat(report): 분석 요청 API 추가`
- 도메인: `auth`, `practice`, `report`, `speech`, `core`, `contracts`, `docs` 중 하나
- 하나의 커밋에는 하나의 목적만 담는다.
- 커밋에 `.env`, API 키, 녹음 파일, 비밀번호를 포함하지 않는다.

## PR
1. 작은 단위로 올린다. 자기 영역 밖 파일이 섞이지 않게 한다.
2. PR 양식(`.github/pull_request_template.md`)의 항목을 모두 채운다.
3. **공용 파일 또는 마이그레이션을 수정했다면**, 작업 전에 팀원 허락을 받았는지 PR에 적는다. (허락 기준은 TEAM.md 4장)
4. 머지는 승인 없이 할 수 있다. 단 머지 전에 `pytest`가 통과하는지 확인한다.
5. 머지 후 `main`을 쓰는 다른 팀원이 알 필요가 있는 변경(환경변수 추가, 마이그레이션, 계약 변경)은 팀 채팅에 알린다.

## 마이그레이션이 포함된 PR
- PR 전에 `main`을 받아서 리비전 번호가 겹치지 않는지 확인한다.
- 머지 후 팀원은 `alembic upgrade head`를 실행해야 한다. PR 설명에 적어 둔다.

## Claude로 작업할 때
- Claude에게 먼저 `docs/TEAM.md`를 읽게 하고, 자신이 누구(BE1/BE2/BE3)인지 알려 준다.
- Claude가 다른 담당 영역이나 공용 파일을 수정하려고 하면 멈추고 팀원 허락부터 받는다.
- Claude가 만든 변경도 사람이 diff를 확인한 뒤에 커밋한다.
