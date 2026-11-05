from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["report"])
# report 도메인 (router) - BE2 담당: 분석 요청/상태, 결과 조회, 비교, AI 피드백
