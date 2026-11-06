"""KSS 낭독 데이터(Hugging Face)의 앞부분 문장들을 이어 붙여 약 2분짜리 테스트용 rec.wav 와 script.txt 를 만든다.
필요: pip install pyarrow huggingface_hub (huggingface_hub 는 faster-whisper 와 함께 설치됨), ffmpeg.
"""
from __future__ import annotations

import argparse
import subprocess
import wave
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

REPO = "Bingsu/KSS_Dataset"
SR = 16000


def download_first_shard() -> str:
    from huggingface_hub import hf_hub_download, list_repo_files

    files = sorted(f for f in list_repo_files(REPO, repo_type="dataset") if f.endswith(".parquet"))
    if not files:
        raise SystemExit("데이터셋에서 parquet 파일을 찾지 못했습니다. 인터넷 연결을 확인하세요.")
    print(f"다운로드: {files[0]} (처음 한 번만 받습니다)")
    return hf_hub_download(REPO, files[0], repo_type="dataset")


def decode(data: bytes) -> np.ndarray:
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-i", "pipe:0", "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        input=data,
        capture_output=True,
    )
    if proc.returncode != 0 or not proc.stdout:
        raise SystemExit("오디오 디코딩 실패: " + proc.stderr.decode("utf-8", errors="ignore")[:200])
    return np.frombuffer(proc.stdout, dtype=np.float32)


def write_wav(path: Path, y: np.ndarray) -> None:
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="my_test_kss", help="결과를 저장할 폴더")
    ap.add_argument("--seconds", type=float, default=110.0, help="목표 길이(초)")
    ap.add_argument("--skip", type=int, default=0, help="앞에서 건너뛸 문장 수")
    ap.add_argument("--parquet", help="이미 받은 parquet 파일 경로 (없으면 자동 다운로드)")
    args = ap.parse_args()

    path = args.parquet or download_first_shard()
    pf = pq.ParquetFile(path)
    names = pf.schema_arrow.names
    if "audio" not in names or "original_script" not in names:
        raise SystemExit(f"예상한 열(audio, original_script)이 없습니다: {names}")

    gap = np.zeros(int(SR * 0.3), dtype=np.float32)
    parts: list[np.ndarray] = []
    texts: list[str] = []
    total = 0.0
    seen = 0
    done = False
    for batch in pf.iter_batches(batch_size=16, columns=["audio", "original_script"]):
        for row in batch.to_pylist():
            seen += 1
            if seen <= args.skip:
                continue
            data = (row["audio"] or {}).get("bytes")
            text = (row["original_script"] or "").strip()
            if not data or not text:
                continue
            y = decode(data)
            parts += [y, gap]
            texts.append(text)
            total += (len(y) + len(gap)) / SR
            if total >= args.seconds:
                done = True
                break
        if done:
            break

    if not parts:
        raise SystemExit("사용할 수 있는 문장을 읽지 못했습니다.")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_wav(out / "rec.wav", np.concatenate(parts))
    (out / "script.txt").write_text("\n".join(texts) + "\n", encoding="utf-8")
    print(f"문장 {len(texts)}개, 약 {total:.0f}초 -> {out / 'rec.wav'}, {out / 'script.txt'}")
    print(
        f"실행: python scripts/run_analyze.py --audio {out}/rec.wav --script-file {out}/script.txt "
        f"--save-words {out}/words.json --out {out}/result.json"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
