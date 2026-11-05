"""음성 분석 진입점 - BE3 담당. FastAPI/DB에 의존하지 않는다."""
from app.contracts.analysis_result import AnalysisResult


def analyze(audio_path: str, script: str) -> AnalysisResult:
    raise NotImplementedError
