# BE 3 음성 분석 모듈 (v1.1)

`analyze(녹음 파일 경로, 대본 문자열) → AnalysisResult(JSON)`

```
app/
├── contracts/analysis_result.py   분석 결과 JSON 스키마 (BE2·BE3·프론트 공통 계약, pydantic)
└── speech/
    ├── analyze.py     진입점 analyze(), warm_up()
    ├── text.py        대본 → 글자 단위, 문장부호 없는 대본의 문장 끝·절 끝(숨 고를 자리) 추정
    ├── align.py       대본-음성 정렬 (닻 2글자, 인식 못 한 구간의 에너지 위치 추정)
    ├── features.py    음높이(반음·7단계), 음량, 늘임, 쉼(기대 여부·상대 길이), 구절별 빠르기
    ├── habits.py      본인 평균 기준 습관 판정, 횟수·위치
    ├── clarity.py     불분명한 구간(건너뜀·인식 어려움·작은 소리) 구간화
    ├── spoken.py      대본과 다르게 말한 단어 (발음 비슷하면 제외)
    ├── disfluency.py  더듬음·끼어든 소리 (군말·반복·대본에 없는 말, 글자 사이의 목소리)
    ├── config.py      모든 임계값 (튜닝은 여기서)
    └── audio_io.py    녹음 → 16kHz 모노 (ffmpeg)
scripts/run_analyze.py   터미널 실행·결과 확인
scripts/calibrate.py     분석 결과 JSON 의 측정값 분포 요약 (임계값 조정용)
scripts/make_kss_sample.py  KSS 낭독 데이터로 기준선 테스트용 음성·대본 생성
tests/                   pytest + 합성 음성 생성기(synth.py)
```

## 1. 설치

1. 이 폴더를 VS Code 로 연다 → 터미널(Ctrl+`)
2. ffmpeg 설치: Windows `winget install ffmpeg` / Mac `brew install ffmpeg`
3. `pip install -r requirements.txt`

## 2. 테스트 순서

```bash
python -m pytest -v

python tests/synth.py samples/demo.wav
python scripts/run_analyze.py --audio samples/demo.wav --script-file samples/demo.txt \
       --words samples/demo_words.json --out samples/demo_result.json

python scripts/run_analyze.py --audio my.m4a --script-file script.txt --save-words words.json --out result.json

python scripts/run_analyze.py --audio my.m4a --script-file script.txt --words words.json

python scripts/run_analyze.py --audio my.m4a --script-file script.txt --filler-prompt --save-words words_f.json --out result_f.json
```

`--filler-prompt` 는 Whisper 가 군말(음, 어)을 지우지 않도록 유도하는 실험 옵션이다. 켜고/끄고 두 번 돌려서 군말이 더 잡히는지 비교한다.

데모 기대 결과: MID_PAUSE x2, END_STRETCH x2, END_RISE x2, '감사합니다' FAST.

실제 녹음 확인 체크리스트
- 문장 끝을 일부러 끌거나 올려 읽은 녹음 / 평소처럼 읽은 녹음에서 결과가 달라지는가
- 문장 중간에 일부러 쉰 곳이 `⏸`로 찍히고, 문장 끝·쉼표 쉼은 안 찍히는가
- 일부러 얼버무린 단어가 `⟨⟩`(unclearRanges)로 표시되는가, 완전히 건너뛴 단어는 SKIPPED 인가
- 문장부호 없는 대본에서 문장 끝이 맞게 잡히는가 (`parse_script` 결과 확인)
- 판정이 너무 많거나 적으면 `config.py` 임계값 조정

## 3. BE 2 연동

```python
from app.speech.analyze import warm_up
@app.on_event("startup")
def _warm(): warm_up()

from app.contracts.analysis_result import AnalysisError
from app.speech.analyze import analyze

def run_analysis(report_id, audio_path, script_snapshot):
    try:
        result = analyze(audio_path, script_snapshot)
        save_result(report_id, result.to_json_dict())
    except AnalysisError as e:
        save_failure(report_id, code=e.code.value, message=e.message)
```

- `analyze()` 는 CPU 를 오래 쓰는 동기 함수이므로 별도 스레드/프로세스 워커에서 호출한다.
- 이전/현재 비교는 두 결과의 `summary`, `habits[].count` 를 비교한다 (BE 2).
- 스키마 파일: `python scripts/export_schema.py`

## 4. 분석 결과 JSON (version 1.1)

idx 는 `spokenText` 의 0-based 글자 인덱스(공백·문장부호 포함, 구간은 양 끝 포함), 시간은 ms, 키는 camelCase.
`spokenText` 는 분석 기준이 되는 텍스트다. 대본을 그대로 읽었으면 대본과 같고(idx 도 대본과 같다), 말하다가 바꾸거나 덧붙였으면 말한 내용이 반영된다. 모든 idx(syllables, pauses, habits, unclearRanges, disfluencies …)는 이 텍스트 기준이다.

### syllables[] (글자 단위)

| 필드 | 뜻 |
| --- | --- |
| idx, char | 대본 글자 위치와 글자 |
| startMs, endMs | 글자가 발음된 구간 |
| pitchHz | 음높이 원본값 (소리가 없으면 null) |
| pitchSt | 본인 평균 대비 반음 차이 (연속값, 곡선 그리기용) |
| pitchLevel | 1~7 단계, 4 = 본인 평균. 경계 −4/−2/−0.7/+0.7/+2/+4 반음 |
| volumeDb | 본인 평균 음량 대비 dB (0 = 평균, 음수 = 작음) |
| lowVolume | 평균보다 14dB 이상 작게 말함 |
| stretch, stretchRatio | 본인 평균보다 길게 끌었는가, 평균 길이 대비 배율 |
| aligned | 음성인식이 이 글자를 확실히 찾음 |
| inferred | 인식은 못 했지만 소리가 있는 자리로 위치를 추정함 (시간값은 근사) |
| confidence | 음성인식 단어 확신도 0~1 (추정/미인식이면 null) |
| isHabit, habitTypes | 이 글자가 습관 위치인가, 종류 |

글자 상태: `aligned=true` 정상 / `aligned=false, inferred=true` 얼버무림(위치 추정) / 둘 다 false 건너뜀(소리 없음).

### pauses[] (쉼)

| 필드 | 뜻 |
| --- | --- |
| afterIdx, durationMs | 이 글자 뒤 쉼, 길이 |
| boundary | 쉼 위치 종류: WORD_INTERNAL / WORD / COMMA / LINE / SENTENCE |
| expected | 대본 구조상 숨 고를 자리인가 (문장 끝·쉼표·줄바꿈·절 끝) |
| relativeLength | 본인의 '보통 쉼'(summary.typicalPauseMs) 대비 배율 |
| isHabit, habitType | 습관으로 확정된 쉼인가, MID_PAUSE 또는 LONG_PAUSE |

### habits[] 종류

| 종류 | 기준 |
| --- | --- |
| END_RISE | 문장의 마지막 음절 음높이가 같은 문장 앞부분보다 +3반음 이상 높음 (물음표 문장 제외) |
| END_STRETCH | 문장 끝 음절을 본인 평균의 2.6배 이상 + 120ms 이상 끎 |
| END_FADE | 문장 끝 음절이 본인 평균 음량보다 14dB 이상 작음 (말끝 흐림) |
| MID_STRETCH | 문장 중간 어절 끝을 평균의 2.2배 이상 끎 |
| MID_PAUSE | 숨 고를 자리가 아닌 곳에서 400ms 이상 쉼 |
| LONG_PAUSE | 숨 고를 자리인데 700ms 이상, 본인 보통 쉼의 2배 이상 쉼 |
| NO_BREAK | 문장이 끝났는데 120ms 미만으로 바로 이어서 말함 |

같은 종류가 2회 이상 반복될 때만 습관으로 보고한다 (`minHabitCount`).

### 그 밖의 필드

- `phrases[]`: 구절별 속도와 FAST/NORMAL/SLOW (본인 평균 대비 1.4배/0.7배). 정렬된 글자가 80% 미만이거나 초당 1.5~11음절을 벗어나는 구절은 판정에서 제외
- `mismatchedRanges[]`: 대본과 인식 결과가 맞지 않은 구간 (inferred 와 건너뜀 모두 포함)
- `unclearRanges[]`: 불분명한 구간. reason = SKIPPED(건너뜀) / LOW_RECOGNITION(인식 어려움) / LOW_VOLUME(작은 소리), confidence 0~1
- `summary`: `scriptMatchRatio`(대본과 일치한 비율), 전체 속도, 쉼 제외 속도, 본인 평균 음높이, 본인 보통 쉼(typicalPauseMs), 정렬 비율
- `disfluencies[]`: 더듬음·끼어든 소리. `beforeIdx` = 이 글자 앞에서 발생, `startMs`/`endMs`, `text`(인식된 말)
  - FILLER: Whisper 가 인식한, 대본에 없는 군말 (어, 음, 그 …) / REPEAT: 방금 말했거나 곧 말할 부분을 다시 말함 / INSERTION: 그 밖의 대본에 없는 말
  - STRAY_SOUND: 대본 글자 사이에 사람 목소리(음높이가 있는 소리)가 150ms 이상 있는데 Whisper 가 말로 인식하지 못함. 숨소리처럼 음높이가 없는 소리는 제외
  - 이런 소리가 들어 있는 구간은 `pauses[]` 에서 빠진다 (조용한 쉼이 아니므로)
- `spokenDifferences[]`: 대본과 확실히 다르게 말한 부분 (분석은 말한 내용 기준). `kind` = REPLACED(바꿔 말함, `scriptText` 에 원래 대본) / ADDED(덧붙여 말함). `startIdx`~`endIdx` 는 `spokenText` 안의 위치. 발음이 비슷한 차이·군말·반복·인식 신뢰도가 낮은 구간은 대본 그대로 둔다 (음성인식 오류일 수 있어서)
- Whisper 는 숫자를 "7시", "200쪽"처럼 적는다. `numerals.py` 가 이를 대본에 있는 읽기(일곱 시, 이백 쪽 / 한 시간, 열 시)로 바꿔 비교한다. 대본에 그 읽기가 없거나 대본이 숫자로 적혀 있으면 바꾸지 않는다
- 준말(되어→돼, 것인→건, 주는→준, 하여→해)은 같은 소리로 본다 (`phonetic.py`). 대본 이탈로 표시하지 않는다
- 쉼·음절 경계는 소리 에너지로 보정한다 (`snap_to_silence`). Whisper 어절 시각은 앞 어절 끝=뒤 어절 시작으로 붙어 나와 문장 끝소리가 잘리고 쉼이 어절 안으로 번지므로, 실제 무음 구간(200ms 이상)에 앞 음절의 끝과 뒤 음절의 시작을 맞춘다. 두 녹음에서 보고된 쉼은 무음 구간과 대부분 ±70ms 안에서 일치한다
- 끼어든 소리(STRAY_SOUND)는 앞뒤 음절과 조용한 틈으로 떨어져 있고, 같은 어절 안이 아니며, 앞 어절의 인식 확신이 낮지 않을 때만 센다. 문장 끝소리의 꼬리나 어절 시각 오차를 끼어든 소리로 세지 않기 위해서다
- 말한 내용으로 바꾸는 기준은 엄격하다: 3음절 이상, 인식 확신도 평균 0.8 이상(단어별 0.5 이상), 소리가 확실히 다를 때만. 그 밖의 불일치(1~2음절, 낮은 확신도)는 음성인식 오류나 약한 발음 차이일 수 있어 대본 글자를 유지하고, Whisper 가 인식한 시각 위에 위치를 잡아 `inferred` 로 표시한다 (건너뜀 아님)
- 불분명 구간(LOW_RECOGNITION)의 `confidence` 는 인식 확신도가 낮고 소리가 많이 다를수록 높다. 화면에는 0.6 이상만 보이는 것을 권장한다
- 대본에서 아예 말하지 않은 부분은 텍스트에 남고 `unclearRanges` 의 SKIPPED 로 표시된다
- `warnings`: PARTIAL_ALIGNMENT, PITCH_UNAVAILABLE, SCRIPT_DEVIATION(대본 일치율 70% 미만. 오류가 아니라 알림)

## 5. 어디를 고치나

| 하고 싶은 일 | 파일 |
| --- | --- |
| 임계값(늘임·쉼·음량·음높이 단계 등) 조정 | `speech/config.py` |
| 문장 끝·절 끝 어미 규칙 보강 | `speech/text.py` 상단의 `_NOUN_YO`, `_NOUN_DA`, `_YO_STEMS`, `_CLAUSE_ENDINGS` |
| 습관 종류 추가·삭제·판정 규칙 | `contracts/analysis_result.py` 의 `HabitType` + `speech/habits.py` |
| 불분명 구간 판정 | `speech/clarity.py` |
| 음성인식 모델 교체·정밀 정렬 | `speech/align.py` 의 Aligner 구현체 |
| JSON 필드 추가 | `contracts/analysis_result.py` (BE2·프론트와 합의 후) |

## 6. 알려진 한계 / 팀에서 정할 것

- WhisperAligner 는 이 개발 환경에서 모델을 내려받지 못해 실제 음성으로는 검증하지 못했다. 합성 음성과 가짜 모델로 연결부만 검증됨. 첫 실제 녹음 테스트가 가장 중요하다.
- 문장부호 없는 대본의 문장 끝·절 끝은 어미 규칙(사전 없음)으로 추정한다. 예외 단어는 `text.py` 목록에 추가한다. 형태소 분석기(kiwipiepy 등)는 연결하지 않았다.
- 음절 단위 시각은 Whisper 어절 시각을 에너지 골로 다듬은 근사값이다. 정밀도가 부족하면 CTC 강제정렬로 Aligner 만 교체한다.
- 얼버무린 구간(inferred)은 소리가 있는 자리에 글자를 배치한 추정값이라 늘임·쉼 판정에서 제외한다.
- 임계값은 KSS 낭독(전문 화자 1명, 약 2분) 분포를 기준으로 정했다. 다른 화자·즉흥 발화·소음 환경에서는 `scripts/calibrate.py` 로 분포를 보고 다시 맞춘다.
- 더듬음은 합성 음성으로만 검증했다. Whisper 는 군말·반복을 지워서 받아쓰는 경우가 많아 FILLER/REPEAT 는 놓칠 수 있고, 그 몫은 STRAY_SOUND(음향 탐지)가 맡는다. 실제 더듬는 녹음으로 확인 전이다. 길게 늘이는 "음~" 같은 소리가 이웃 글자와 붙어 있으면 분리하지 못한다.
- 숫자·영문은 Whisper 가 읽은 형태와 대본 글자가 달라 위치를 잡지 못한다.
- 팀 합의 필요: ① idx 0-based ② 습관 종류 목록(기획의 '쪼 구분 기준') ③ JSON 1.1 추가 필드 ④ 임계값
