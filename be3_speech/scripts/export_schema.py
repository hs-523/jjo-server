"""분석 결과 JSON Schema 를 app/contracts/analysis_result.schema.json 으로 내보낸다. BE2·프론트와 계약을 공유할 때 쓴다."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.contracts.analysis_result import AnalysisResult

out = ROOT / "app" / "contracts" / "analysis_result.schema.json"
out.write_text(
    json.dumps(AnalysisResult.model_json_schema(by_alias=True), ensure_ascii=False, indent=2), encoding="utf-8"
)
print("wrote", out)
