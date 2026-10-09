"""명령줄 진입점. 하위 명령(classify 등)을 여기서 연결한다."""

import argparse
from pathlib import Path

from immersive_tts import __version__


def cmd_classify(args: argparse.Namespace) -> int:
    text = args.file.read_text(encoding="utf-8")
    print(f"{args.file.name}: {len(text):,}자 읽음")
    print("분류기는 아직 구현 전입니다.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="immersive-tts")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("classify", help="텍스트가 문학인지 비문학인지 분류")
    p.add_argument("file", type=Path, help="분류할 텍스트 파일(UTF-8)")
    p.set_defaults(func=cmd_classify)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
