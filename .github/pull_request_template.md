## 배경
<!-- 왜 이 작업이 필요한가요? 관련 이슈나 논의가 있다면 링크 -->

## 변경 내용
<!-- 무엇을 바꿨나요? 주요 파일과 동작 위주로 -->
-

## 공용 파일 수정 여부
<!-- contracts, core/config.py, core/database.py, main.py, pyproject.toml, alembic/env.py, .env.example, docs -->
- [ ] 수정하지 않음
- [ ] 수정함 → 파일: 
- [ ] 작업 전에 팀원 허락을 받음 (누구에게, 어디서: )

## 마이그레이션 여부
- [ ] 없음
- [ ] 있음 → 파일: `alembic/versions/`
  - [ ] 작업 전에 팀원 허락을 받음
  - [ ] `main`을 받아서 리비전 번호가 겹치지 않음
  - [ ] 생성된 마이그레이션을 열어서 확인함 (CHECK 제약, enum 등)
  - [ ] 머지 후 팀원이 `alembic upgrade head`를 실행해야 함

## 테스트
- [ ] `pytest` 통과
- [ ] 변경한 동작을 직접 확인함 (방법: )
- [ ] 내 담당 영역 밖의 파일을 수정하지 않음
- [ ] `.env`, API 키 등 비밀 값이 포함되지 않음
