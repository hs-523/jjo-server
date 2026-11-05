from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])
# auth 도메인 (router) - BE1 담당: 로그인/회원가입, 약관 동의, 사용자 설정
