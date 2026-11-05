"""분석 결과 JSON 스키마 (BE2/BE3/프론트엔드 공용 계약).

TODO: BE3 PoC 결과가 나오면 아래 예시를 기준으로 Pydantic 모델로 확정한다.
      확정 전까지는 형태 참고용이며, 수정은 BE2/BE3/프론트 합의 후에만 한다.

형태 예시 (역할 분담 문서 기준):

    {
      "version": "1.0",
      "durationMs": 68000,
      "syllables": [
        { "idx": 1, "char": "지", "startMs": 320, "endMs": 410,
          "pitchLevel": 2, "stretch": false, "isHabit": true }
      ],
      "pauses": [
        { "afterIdx": 312, "durationMs": 800, "isHabit": true }
      ],
      "phrases": [
        { "startIdx": 120, "endIdx": 145, "speedRatio": 1.3, "speedLabel": "FAST" }
      ],
      "habits": [
        { "type": "END_RISE", "count": 4,
          "occurrences": [ { "startIdx": 30, "endIdx": 34 } ],
          "firstIdx": 30 }
      ],
      "summary": { "avgSyllablesPerSec": 5.2 }
    }

미확정 항목 (PoC 후 결정):
- idx 기준: 원문 기준 글자 인덱스(공백 포함)가 권장안. 0부터인지 1부터인지 미정 (예시는 1)
- pitchLevel: 값 범위/단계 수 미정. 음높이 원본값(Hz 등) 필드를 함께 줄지 미정
- stretch: 여부(bool)만 줄지, 늘임 비율도 줄지 미정
- speedLabel: 예시는 "FAST"뿐. 전체 값 목록(FAST/NORMAL/SLOW 등) 미정
- habits.type: 습관 종류 고정 목록 미정 (예시는 END_RISE뿐)
- 대본과 다르게 읽은 구간 처리, 분석 실패 시 사유 표현 방식 미정
"""
from typing import Any

# TODO: PoC 후 Pydantic 모델로 교체. speech/analyze.py가 이 이름을 import한다.
AnalysisResult = dict[str, Any]
