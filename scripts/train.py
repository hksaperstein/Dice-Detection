#!/usr/bin/env python3
"""Train YOLO11s dice detector.

Variants (spec 2026-07-10-dice-detector-v1):
  s        - synthetic detection_v1 only
  s_plus_r - synthetic + real finetune slice mixed into training
Both validate on the synthetic val split during training (monitoring only);
the frozen real test set is never seen here.
"""
import argparse
from pathlib import Path

from ultralytics import YOLO

CLASS_NAMES = ["d4", "d6", "d8", "d10", "d10_pct", "d12", "d20"]
REPO = Path(__file__).resolve().parents[1]


def build_s_plus_r_yaml():
    out = REPO / "data/yolo/dice_s_plus_r.yaml"
    out.write_text(
        "path: .\n"
        "train:\n"
        f"  - {(REPO / 'data/yolo/images/train').resolve()}\n"
        f"  - {(REPO / 'data/real/finetune/images').resolve()}\n"
        f"val: {(REPO / 'data/yolo/images/val').resolve()}\n"
        "names:\n"
        + "".join(f"  {i}: {n}\n" for i, n in enumerate(CLASS_NAMES))
    )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["s", "s_plus_r"], required=True)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--imgsz", type=int, default=640)
    args = ap.parse_args()

    data = (REPO / "data/yolo/dice.yaml" if args.variant == "s"
            else build_s_plus_r_yaml())
    model = YOLO("yolo11s.pt")
    model.train(
        data=str(data),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        seed=42,
        deterministic=True,
        project=str(REPO / "models/runs"),
        name=args.variant,
        exist_ok=True,
        device=0,
    )
    print(f"[DONE] best weights: models/runs/{args.variant}/weights/best.pt")


if __name__ == "__main__":
    main()
