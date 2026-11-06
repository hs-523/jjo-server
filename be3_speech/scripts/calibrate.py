"""분석 결과 JSON 에서 문장 끝 늘임·음량·음높이, 어절 끝 늘임, 구절 속도, 쉼의 분포(백분위수)와 현재 임계값 초과 비율을 요약한다.
깨끗한 낭독 결과로 돌려서 임계값이 정상 발화를 얼마나 습관으로 잡는지 확인하는 데 쓴다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.speech.config import DEFAULT_CONFIG as C


def show(name: str, values: list[float], limit: float | None = None, above: bool = True) -> None:
    if not values:
        print(f"{name:30s} (자료 없음)")
        return
    a = np.array(values, dtype=float)
    p10, p50, p90, p95 = np.percentile(a, [10, 50, 90, 95])
    line = f"{name:30s} n={len(a):3d}  p10={p10:7.2f} p50={p50:7.2f} p90={p90:7.2f} p95={p95:7.2f} max={a.max():7.2f}"
    if limit is not None:
        hit = float(np.mean(a >= limit if above else a <= limit))
        line += f"  | 기준 {limit}: {hit:.0%} 초과"
    print(line)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", required=True)
    args = ap.parse_args()
    d = json.loads(Path(args.result).read_text(encoding="utf-8"))
    syl = d["syllables"]
    n = len(syl)

    ends = [False] * n
    for i in range(n - 1):
        if syl[i + 1]["idx"] - syl[i]["idx"] >= 3:
            ends[i] = True
    ends[-1] = True

    aligned = [s for s in syl if s["aligned"]]
    dur = [s["endMs"] - s["startMs"] for s in aligned]
    print(f"음절 {n}개 (정렬 {len(aligned)}, 추정 {sum(s['inferred'] for s in syl)}), 문장 약 {sum(ends)}개")
    show("음절 길이 ms", dur)
    print(f"  60ms 이하 음절: {sum(1 for x in dur if x <= 60)}개 ({np.mean(np.array(dur) <= 60):.0%})")

    final = [syl[i] for i in range(n) if ends[i] and syl[i]["aligned"]]
    inner = [syl[i] for i in range(n) if not ends[i] and syl[i]["aligned"] and syl[i]["char"].strip()]
    show("문장 끝 늘임 배율", [s["stretchRatio"] for s in final], C.end_stretch_ratio)
    show("그 외 음절 늘임 배율", [s["stretchRatio"] for s in inner], C.stretch_ratio)
    show("문장 끝 음량 dB", [s["volumeDb"] for s in final if s["volumeDb"] is not None], -C.low_volume_db, above=False)
    show("그 외 음절 음량 dB", [s["volumeDb"] for s in inner if s["volumeDb"] is not None], -C.low_volume_db, above=False)

    rise_last, rise_pen = [], []
    cur: list[dict] = []
    for i in range(n):
        cur.append(syl[i])
        if not ends[i]:
            continue
        pitched = [x for x in cur if x["pitchSt"] is not None]
        head = [x["pitchSt"] for x in cur[:-2] if x["pitchSt"] is not None]
        if len(pitched) >= C.end_rise_min_pitched and head:
            med = float(np.median(head))
            if cur[-1]["pitchSt"] is not None:
                rise_last.append(cur[-1]["pitchSt"] - med)
            if len(cur) > 1 and cur[-2]["pitchSt"] is not None:
                rise_pen.append(cur[-2]["pitchSt"] - med)
        cur = []
    show("문장 끝 음높이 차 반음", rise_last, C.end_rise_st)
    show("끝에서 둘째 음높이 차 반음", rise_pen)

    show("구절 속도 배율", [p["speedRatio"] for p in d["phrases"]])
    show("구절 속도 음절/초", [p["speedSyllPerSec"] for p in d["phrases"]])
    exp = [p for p in d["pauses"] if p["expected"]]
    unexp = [p for p in d["pauses"] if not p["expected"]]
    show("숨 고를 자리 쉼 ms", [p["durationMs"] for p in exp])
    show("숨 고를 자리 쉼 상대 길이", [p["relativeLength"] for p in exp], C.long_pause_relative)
    show("그 외 자리 쉼 ms", [p["durationMs"] for p in unexp], C.habit_pause_ms)

    print("\n[현재 결과의 습관]")
    for h in d["habits"]:
        print(f"  {h['type']:12s} x{h['count']}")
    if not d["habits"]:
        print("  (없음)")
    print(f"불분명 구간 {len(d['unclearRanges'])}개, 정렬 {d['summary']['alignedRatio']:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
