"""원본 데이터 살펴보기.

출처마다 파일 구조, 메타데이터 분포, 본문 샘플을 출력한다.
전처리 코드를 짜기 전에 "데이터가 실제로 어떻게 생겼는지" 확인하는 용도다.
압축은 풀지 않고 zip/bz2 안을 바로 읽는다.

사용 예 (레포 루트에서):
    python scripts/inspect_raw.py book --kdc 810
    python scripts/inspect_raw.py news
    python scripts/inspect_raw.py paper
    python scripts/inspect_raw.py wikisource --pages 20000
"""

import argparse
import bz2
import json
import random
import re
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

RAW = Path("data/raw")
BOOK = RAW / "029.대규모 구매도서 기반 한국어 말뭉치 데이터/01.데이터/1.Training"
NEWS = RAW / "문서요약 텍스트/Validation"
PAPER = RAW / "018.논문자료 요약 데이터/01.데이터/2. Validation/1. 라벨링데이터_231101_add"
WIKI = RAW / "wikisource/kowikisource-20261001-pages-articles.xml.bz2"

# 대사로 볼 만한 따옴표 (곧은 따옴표와 둥근 따옴표 모두)
QUOTE_RE = re.compile(r"[\"“”「」『』]")


def header(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def short(text: str, n: int = 200) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n] + "…"


def zip_name(info: zipfile.ZipInfo) -> str:
    """zip 안의 한글 파일 이름 복원.

    윈도우에서 만든 zip은 파일 이름을 cp949로 저장해 두는데,
    파이썬은 이를 cp437로 읽어서 글자가 깨진다. 거꾸로 되돌려 준다.
    """
    if info.flag_bits & 0x800:  # UTF-8 표시가 있으면 그대로
        return info.filename
    try:
        return info.filename.encode("cp437").decode("cp949")
    except UnicodeError:
        return info.filename


# ---------------------------------------------------------------- 구매도서
def inspect_book(args: argparse.Namespace) -> None:
    path = BOOK / "라벨링데이터" / f"TL_{args.kdc}.zip"
    header(f"구매도서 말뭉치: {path.name}")
    z = zipfile.ZipFile(path)
    names = [n for n in z.namelist() if "_TEXT_" in n]
    print(f"TEXT 파일 {len(names)}개 (이 중 앞에서 {args.chunks}개만 읽음)")
    print(z.read(next(n for n in z.namelist() if n.endswith("_INFO.json"))).decode())

    paragraphs = []
    for name in names[: args.chunks]:
        paragraphs += json.loads(z.read(name))["paragraphs"]

    # 세부 KDC(예: 813 소설)가 문단마다 붙어 있는지, 책을 구분할 단서가 있는지 본다
    kdc = Counter(p["info"]["kdc"] for p in paragraphs)
    authors = Counter(
        (p["info"]["author"].get("birth_year"), tuple(p["info"]["author"].get("jobs", [])))
        for p in paragraphs
    )
    print(f"문단 {len(paragraphs):,}개")
    print("세부 KDC 분포:", kdc.most_common(15))
    print(f"서로 다른 (작가 출생연도, 직업) 조합: {len(authors)}개")
    print("info 필드 예시:", json.dumps(paragraphs[0]["info"], ensure_ascii=False))

    # 연속한 문단이 같은 책에서 왔는지(작가 정보가 이어지는지) 확인
    changes = sum(
        paragraphs[i]["info"]["author"] != paragraphs[i - 1]["info"]["author"]
        for i in range(1, len(paragraphs))
    )
    print(f"이웃 문단끼리 작가 정보가 바뀌는 횟수: {changes:,}회")

    print("\n[샘플 문단]")
    random.seed(0)
    for p in random.sample(paragraphs, min(args.samples, len(paragraphs))):
        text = " ".join(s["text"] for s in p["sentences"])
        q = len(QUOTE_RE.findall(text))
        print(f"- ({p['id']}, kdc {p['info']['kdc']}, 따옴표 {q}개) {short(text)}")


# ---------------------------------------------------------------- 신문기사·사설
def inspect_news(args: argparse.Namespace) -> None:
    for kind in ["신문기사", "사설"]:
        path = NEWS / f"{kind}_valid_original.zip"
        header(f"문서요약 텍스트: {path.name}")
        z = zipfile.ZipFile(path)
        data = json.loads(z.read(z.namelist()[0]))
        docs = data["documents"]
        print(f"문서 {len(docs):,}개, 문서 필드: {list(docs[0].keys())}")
        print("category 분포:", Counter(d["category"] for d in docs).most_common(10))
        print("media_name 상위:", Counter(d["media_name"] for d in docs).most_common(5))

        random.seed(0)
        for d in random.sample(docs, args.samples):
            # text는 [문단][문장] 2단 리스트
            text = " ".join(s["sentence"] for para in d["text"] for s in para)
            q = len(QUOTE_RE.findall(text))
            print(f"- ({d['id']}, {d['category']}, 따옴표 {q}개) {d['title']}\n    {short(text)}")


# ---------------------------------------------------------------- 논문
def inspect_paper(args: argparse.Namespace) -> None:
    path = PAPER / "validation_논문.zip"
    header(f"논문자료 요약: {path.name}")
    z = zipfile.ZipFile(path)
    for info in z.infolist():
        print(f"  {zip_name(info)}  {info.file_size:,} bytes")
    member = next(i for i in z.infolist() if i.filename.endswith(".json"))
    data = json.loads(z.read(member))
    docs = data[0]["data"]
    print(f"문서 {len(docs):,}개, 문서 필드: {list(docs[0].keys())}")
    print("ipc(분야) 분포:", Counter(d["ipc"] for d in docs).most_common(10))
    first = docs[0]
    for key in ["summary_entire", "summary_section"]:
        if key in first:
            print(f"{key} 첫 항목 필드: {list(first[key][0].keys())}")

    random.seed(0)
    for d in random.sample(docs, args.samples):
        text = d["summary_entire"][0]["orginal_text"]  # 원본 필드 이름이 orginal(오타)
        print(f"- ({d['doc_id']}, {d['ipc']}) {d['title']}\n    {short(text)}")


# ---------------------------------------------------------------- 위키문헌
def inspect_wikisource(args: argparse.Namespace) -> None:
    header(f"위키문헌 덤프: {WIKI.name} (앞에서 {args.pages:,}쪽)")
    cat_re = re.compile(r"\[\[분류:([^\]|]+)")
    namespaces, cats = Counter(), Counter()
    samples = []
    seen = 0

    # iterparse: 148MB 압축 XML을 메모리에 다 올리지 않고 한 페이지씩 읽는다
    with bz2.open(WIKI) as f:
        for _, el in ET.iterparse(f):
            if not el.tag.endswith("}page"):
                continue
            ns = el.findtext("{*}ns")
            title = el.findtext("{*}title")
            text = el.findtext("{*}revision/{*}text") or ""
            namespaces[ns] += 1
            if ns == "0" and not text.startswith("#넘겨주기"):
                cats.update(cat_re.findall(text))
                if len(samples) < 2000:
                    samples.append((title, text))
            el.clear()  # 읽은 페이지는 메모리에서 비운다
            seen += 1
            if seen >= args.pages:
                break

    print("이름공간(ns) 분포:", namespaces.most_common(10), "(0이 본문 문서)")
    print("\n분류 태그 상위 30개:")
    for c, n in cats.most_common(30):
        print(f"  {n:6,}  {c}")

    random.seed(0)
    print("\n[샘플 문서]")
    for title, text in random.sample(samples, min(args.samples, len(samples))):
        q = len(QUOTE_RE.findall(text))
        print(f"- {title} (따옴표 {q}개)\n    {short(text, 300)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--samples", type=int, default=5, help="출력할 샘플 개수")
    sub = parser.add_subparsers(dest="source", required=True)

    p = sub.add_parser("book", help="구매도서 말뭉치")
    p.add_argument("--kdc", default="810", help="zip 번호(KDC), 예: 810, 320")
    p.add_argument("--chunks", type=int, default=3, help="읽을 TEXT 파일 개수")
    p.set_defaults(func=inspect_book)

    sub.add_parser("news", help="신문기사·사설").set_defaults(func=inspect_news)
    sub.add_parser("paper", help="논문").set_defaults(func=inspect_paper)

    p = sub.add_parser("wikisource", help="위키문헌 덤프")
    p.add_argument("--pages", type=int, default=20000, help="읽을 페이지 수")
    p.set_defaults(func=inspect_wikisource)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
