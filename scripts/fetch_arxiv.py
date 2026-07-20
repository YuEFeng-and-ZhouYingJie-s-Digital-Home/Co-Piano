"""
fetch_arxiv.py — 一次性抓取 10 组查询的 arxiv 论文,合并去重,落盘元数据 + PDF + 文本。

Usage:
    python3 scripts/fetch_arxiv.py [--max-per-query 25] [--workers 3]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPERS = ROOT / "papers"
PDFS = ROOT / "pdfs"
PARSED = ROOT / "parsed"
QUERIES_FILE = ROOT / "scripts" / "queries.txt"

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def load_queries() -> list[tuple[str, str]]:
    """读取 queries.txt,返回 [(name, query_string), ...]"""
    out: list[tuple[str, str]] = []
    name_re = re.compile(r"^#\s*(\S.*?)\s*$")
    for line in QUERIES_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("# 搜索"):
            continue
        if s.startswith("#"):
            m = name_re.match(s)
            if m:
                name = m.group(1).strip()
            else:
                continue
        else:
            name = f"q{len(out)+1}"
            out.append((name, s))
    return out


def fetch_atom(query: str, max_results: int = 25) -> list[dict]:
    """调用 arxiv API,返回每条的元数据 dict(只解析 Atom,PDF 链接另算)
    arxiv 期望空格分隔 term,不在 URL 中编码。+ 在 arxiv API 中被解析为空格。
    """
    # 直接把 + 还原成空格,保留其他符号原样
    q = query.replace("+", " ")
    # 只对空格和 & = 编码,其他保留
    q = urllib.parse.quote(q, safe="()\"'/:")
    url = (
        f"http://export.arxiv.org/api/query?search_query={q}"
        f"&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "piano-ai-corpus/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    root = ET.fromstring(data)
    entries = []
    for e in root.findall("atom:entry", NS):
        arxiv_id_full = e.find("atom:id", NS).text.strip()  # http://arxiv.org/abs/xxxx
        arxiv_id = arxiv_id_full.rsplit("/", 1)[-1]
        # 清理版本号 v1/v2
        arxiv_id_base = re.sub(r"v\d+$", "", arxiv_id)
        title = " ".join(e.find("atom:title", NS).text.split())
        summary = " ".join(e.find("atom:summary", NS).text.split())
        published = e.find("atom:published", NS).text
        updated = e.find("atom:updated", NS).text
        authors = [
            " ".join(a.find("atom:name", NS).text.split())
            for a in e.findall("atom:author", NS)
        ]
        cats = [
            c.attrib.get("term", "")
            for c in e.findall("atom:category", NS)
        ]
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id_base}"
        entries.append({
            "arxiv_id": arxiv_id_base,
            "title": title,
            "summary": summary,
            "authors": authors,
            "published": published,
            "updated": updated,
            "categories": cats,
            "pdf_url": pdf_url,
            "abs_url": f"https://arxiv.org/abs/{arxiv_id_base}",
        })
    return entries


def write_meta(entries: list[dict], query_name: str) -> int:
    """把元数据落盘为 papers/<id>.json,返回新增数(去重后)"""
    PAPERS.mkdir(parents=True, exist_ok=True)
    new = 0
    for e in entries:
        p = PAPERS / f"{e['arxiv_id']}.json"
        if p.exists():
            continue
        e["fetched_at"] = datetime.utcnow().isoformat() + "Z"
        e["query_name"] = query_name
        e["pdf_status"] = "pending"
        e["parse_status"] = "pending"
        p.write_text(json.dumps(e, ensure_ascii=False, indent=2), encoding="utf-8")
        new += 1
    return new


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-per-query", type=int, default=25)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--queries", type=str, default="")
    args = ap.parse_args()

    queries = load_queries()
    if args.queries:
        wanted = set(args.queries.split(","))
        queries = [q for q in queries if q[0] in wanted]

    print(f"[fetch] 启动 {len(queries)} 组查询,每组 {args.max_per_query} 篇")
    all_entries: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_atom, q, args.max_per_query): name for name, q in queries}
        for fut in as_completed(futs):
            name = futs[fut]
            try:
                ents = fut.result()
                print(f"  - {name}: {len(ents)} 篇")
                all_entries.extend(ents)
            except Exception as ex2:
                print(f"  ! {name}: {ex2}")

    # 去重
    seen = set()
    uniq = []
    for e in all_entries:
        if e["arxiv_id"] in seen:
            continue
        seen.add(e["arxiv_id"])
        uniq.append(e)
    print(f"[fetch] 共 {len(uniq)} 篇(去重后)")

    # 落盘
    by_query: dict[str, list[dict]] = {}
    for e in uniq:
        by_query.setdefault(e.get("query_name", "?"), []).append(e)

    total_new = 0
    for qname, ents in by_query.items():
        n = write_meta(ents, qname)
        total_new += n
        print(f"  → {qname}: 新增 {n} 篇")
    print(f"[fetch] 落盘完成,本次新增 {total_new} 篇,累计 {len(list(PAPERS.glob('*.json')))} 篇")


if __name__ == "__main__":
    main()
