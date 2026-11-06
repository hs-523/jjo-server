"""녹음 파일과 대본을 넣어 분석을 실행하고 결과를 터미널에 보여주며 JSON 으로 저장하는 스크립트. 사용법은 README 참고."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.contracts.analysis_result import AnalysisError
from app.speech.align import EnergyAligner, PrecomputedWordsAligner, WhisperAligner, WordTiming
from app.speech.analyze import analyze
from app.speech.audio_io import load_audio
from app.speech.config import DEFAULT_CONFIG
from app.speech.text import parse_script

REASON_KO = {"LOW_VOLUME": "작은 소리", "LOW_RECOGNITION": "인식 어려움", "SKIPPED": "건너뜀"}
DISFLUENCY_KO = {"FILLER": "군말", "REPEAT": "반복", "INSERTION": "끼어든 말", "STRAY_SOUND": "끼어든 소리"}


def mark_script(script: str, result) -> str:
    text = result.spoken_text or script
    habit = {s.idx for s in result.syllables if s.is_habit}
    unclear = set()
    for r in result.unclear_ranges:
        unclear.update(range(r.start_idx, r.end_idx + 1))
    pause_after = {p.after_idx: p for p in result.pauses if p.is_habit}
    disfl = {d.before_idx: d for d in result.disfluencies}
    diff = {d.start_idx: d for d in result.spoken_differences}
    in_diff = {i for d in result.spoken_differences for i in range(d.start_idx, d.end_idx + 1)}
    out = []
    for i, ch in enumerate(text):
        if i in disfl:
            d = disfl[i]
            out.append(f" 〔{DISFLUENCY_KO[d.type.value]}{' ' + d.text if d.text else ''}〕 ")
        if i in diff:
            d = diff[i]
            out.append(f"《{d.spoken}←{d.script_text}》" if d.script_text else f"《＋{d.spoken}》")
        if i in in_diff:
            continue
        out.append(f"【{ch}】" if i in habit else f"⟨{ch}⟩" if i in unclear else ch)
        if i in pause_after:
            p = pause_after[i]
            out.append(f" ⏸{p.duration_ms}ms ")
    return "".join(out)


def print_report(script: str, result, elapsed: float) -> None:
    script = result.spoken_text or script
    sm = result.summary
    print(f"\n=== 분석 완료 ({elapsed:.1f}s) ===")
    print(f"녹음 {result.duration_ms / 1000:.1f}s | 전체 속도 {sm.avg_syllables_per_sec} 음절/초 "
          f"(쉼 제외 {sm.articulation_syllables_per_sec}) | 본인 평균 음높이 {sm.median_pitch_hz} Hz | "
          f"보통 쉼 {sm.typical_pause_ms}ms | 정렬 {sm.aligned_ratio:.0%} | 대본과 일치 "
          f"{'-' if sm.script_match_ratio is None else format(sm.script_match_ratio, '.0%')}")
    if result.warnings:
        print("경고:", ", ".join(result.warnings))
    print("\n[습관]")
    if not result.habits:
        print("  (반복된 습관 없음)")
    start_of = {x.idx: x.start_ms for x in result.syllables}
    for h in result.habits:
        spots = ", ".join(f"'{script[o.start_idx:o.end_idx + 1]}'@{start_of.get(o.start_idx, 0) / 1000:.1f}s" for o in h.occurrences)
        print(f"  {h.type.value:12s} x{h.count}  {spots}")
    print("\n[빠르기 구절]")
    for p in result.phrases:
        if p.speed_label.value != "NORMAL":
            print(f"  {p.speed_label.value:5s} x{p.speed_ratio}  '{script[p.start_idx:p.end_idx + 1]}'")
    if result.unclear_ranges:
        start_of = {x.idx: x.start_ms for x in result.syllables}
        ranked = sorted(result.unclear_ranges, key=lambda r: -r.confidence)
        shown = [r for r in ranked if r.confidence >= 0.6]
        print(f"\n[불분명한 구간]  전체 {len(ranked)}개 중 확신 0.6 이상 {len(shown)}개 (확신 높은 순)")
        for r in shown[:25]:
            print(f"  {start_of.get(r.start_idx, 0) / 1000:6.1f}s  {REASON_KO[r.reason.value]:8s} 확신 {r.confidence:.2f}  '{script[r.start_idx:r.end_idx + 1]}'")
        if len(shown) > 25:
            print(f"  … 외 {len(shown) - 25}개")
    if result.spoken_differences:
        print("\n[대본과 다르게 말한 부분]  (위치·분석은 말한 내용 기준)")
        for d in result.spoken_differences:
            print(f"  {'바꿔 말함' if d.script_text else '덧붙여 말함'}  '{d.script_text or ''}' → '{d.spoken}'")
    if result.disfluencies:
        counts = {}
        for d in result.disfluencies:
            key = f"{DISFLUENCY_KO[d.type.value]}" + (f" '{d.text}'" if d.text else "")
            counts[key] = counts.get(key, 0) + 1
        print("\n[더듬음·끼어든 소리]  집계: " + ", ".join(f"{k} {v}회" for k, v in counts.items()))
        for d in result.disfluencies:
            before = script[d.before_idx : d.before_idx + 4]
            label = DISFLUENCY_KO[d.type.value] + (f" '{d.text}'" if d.text else "")
            print(f"  {label:14s} {d.start_ms}~{d.end_ms}ms ({d.end_ms - d.start_ms}ms)  '{before}' 앞")
    print("\n[대본 표시]  【】=습관 음절  ⏸=습관 쉼  ⟨⟩=불분명한 구간  〔〕=더듬음·끼어든 소리  《》=말한 단어←대본")
    print(mark_script(script, result))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--script")
    g.add_argument("--script-file")
    ap.add_argument("--aligner", choices=["whisper", "energy"], default="whisper")
    ap.add_argument("--model", default="small", help="faster-whisper 모델 (tiny/base/small/medium)")
    ap.add_argument("--words", help="저장해둔 어절 시각 JSON 사용 (Whisper 생략)")
    ap.add_argument("--save-words", help="Whisper 어절 시각을 JSON 으로 저장")
    ap.add_argument("--script-prompt", action="store_true", help="Whisper 에 대본을 힌트로 전달 (실험)")
    ap.add_argument("--filler-prompt", action="store_true", help="Whisper 가 군말(음/어)을 지우지 않도록 유도 (실험)")
    ap.add_argument("--out", help="분석 결과 JSON 저장 경로")
    args = ap.parse_args()

    script = args.script or Path(args.script_file).read_text(encoding="utf-8").strip()
    t0 = time.time()
    try:
        if args.words:
            raw = json.loads(Path(args.words).read_text(encoding="utf-8"))
            aligner = PrecomputedWordsAligner([WordTiming(**w) for w in raw])
        elif args.aligner == "energy":
            print("[주의] energy aligner 는 음절 길이가 고르다고 가정하는 개발용입니다. 실제 녹음은 whisper 를 쓰세요.",
                  file=sys.stderr)
            aligner = EnergyAligner()
        else:
            aligner = WhisperAligner(
                model_size=args.model, use_script_prompt=args.script_prompt, filler_prompt=args.filler_prompt
            )
            if args.save_words:
                y = load_audio(args.audio, DEFAULT_CONFIG)
                words = aligner.transcribe_words(y, "".join(u.char for u in parse_script(script)))
                Path(args.save_words).write_text(
                    json.dumps([w.__dict__ for w in words], ensure_ascii=False, indent=1), encoding="utf-8"
                )
                print(f"어절 시각 {len(words)}개 저장: {args.save_words}")
                aligner = PrecomputedWordsAligner(words)
        result = analyze(args.audio, script, aligner=aligner)
    except AnalysisError as e:
        print(f"분석 실패: {e}", file=sys.stderr)
        return 1

    print_report(script, result, time.time() - t0)
    if args.out:
        Path(args.out).write_text(result.to_json(indent=2), encoding="utf-8")
        print(f"\nJSON 저장: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
