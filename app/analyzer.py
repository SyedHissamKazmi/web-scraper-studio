from __future__ import annotations

import re
from collections import Counter
from io import BytesIO
from urllib.parse import urlparse

import pandas as pd


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?){1,3}\d{3,4}")

STOPWORDS = {
    "this", "that", "with", "have", "from", "they", "will", "your",
    "which", "there", "their", "about", "would", "could", "should",
    "these", "those", "been", "were", "when", "what", "into", "also",
    "than", "then", "them", "such", "only", "some", "more", "most",
    "many", "very", "each", "other", "over", "just", "like",
}


def extract_emails(content: str) -> list[str]:
    return sorted(set(EMAIL_RE.findall(content)))


def extract_phones(content: str) -> list[str]:
    raw = PHONE_RE.findall(content)
    cleaned = []
    for p in raw:
        digits = re.sub(r"\D", "", p)
        if 8 <= len(digits) <= 15:
            cleaned.append(p.strip())
    return sorted(set(cleaned))[:30]


def word_frequency(content: str, top_n: int = 20) -> list[tuple[str, int]]:
    words = re.findall(r"\b[a-z]{4,}\b", content.lower())
    filtered = [w for w in words if w not in STOPWORDS]
    return Counter(filtered).most_common(top_n)


def build_dataframe(headings: list[str], links: list[str]) -> pd.DataFrame:
    max_len = max(len(headings), len(links), 1)
    headings = headings + [""] * (max_len - len(headings))
    links = links + [""] * (max_len - len(links))
    return pd.DataFrame({
        "Target Page Titles & Headings": headings,
        "Extracted Resource Links": links,
    })


def extract_host(url: str) -> str:
    try:
        if not str(url).startswith("http"):
            return ""
        return urlparse(str(url)).netloc.replace("www.", "")
    except Exception:
        return ""


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    metrics = {"initial_rows": len(df)}

    df.columns = df.columns.str.strip()
    headings_col = "Target Page Titles & Headings"
    links_col = "Extracted Resource Links"

    df[headings_col] = df[headings_col].fillna("").astype(str)
    df[links_col] = df[links_col].fillna("").astype(str)

    df[headings_col] = df[headings_col].str.upper().str.strip()
    df = df[df[links_col].str.startswith("http")]

    df["Extracted Network Host"] = df[links_col].apply(extract_host)
    metrics["isolated_domains"] = df["Extracted Network Host"].nunique()

    before = len(df)
    df = df.drop_duplicates(subset=[links_col], keep="first")
    metrics["removed_duplicates"] = before - len(df)
    metrics["final_rows"] = len(df)

    return df, metrics


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer.getvalue()