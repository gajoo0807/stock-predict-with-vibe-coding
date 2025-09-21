from __future__ import annotations
from typing import List


def approx_token_count(text: str) -> int:
    # Fallback when tiktoken not available
    if not text:
        return 0
    return max(1, len(text) // 4)


def count_tokens(text: str) -> int:
    try:
        import tiktoken  # type: ignore

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return approx_token_count(text)


def split_text(text: str, target_tokens: int = 800, min_tokens: int = 300) -> List[str]:
    if not text:
        return []

    # Split by paragraphs and sentences
    import re

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    sentences: List[str] = []
    for p in paragraphs:
        sentences.extend([s.strip() for s in re.split(r"(?<=[。.!?])\s+|\n", p) if s.strip()])

    chunks: List[str] = []
    buf: List[str] = []
    buf_tokens = 0
    for s in sentences:
        st = count_tokens(s)
        if buf_tokens + st > target_tokens and buf_tokens >= min_tokens:
            chunks.append(" ".join(buf))
            buf = [s]
            buf_tokens = st
        else:
            buf.append(s)
            buf_tokens += st

    if buf:
        if buf_tokens < min_tokens and chunks:
            # merge with previous
            prev = chunks.pop()
            merged = prev + " " + " ".join(buf)
            chunks.append(merged)
        else:
            chunks.append(" ".join(buf))

    # ensure each chunk roughly 500-1000 tokens; if still too long, hard cut
    final_chunks: List[str] = []
    for ch in chunks:
        tokens = count_tokens(ch)
        if tokens <= 1000:
            final_chunks.append(ch)
        else:
            # hard split
            words = ch.split()
            cur: List[str] = []
            cur_tokens = 0
            for w in words:
                wt = count_tokens(w)
                if cur_tokens + wt > target_tokens and cur_tokens >= min_tokens:
                    final_chunks.append(" ".join(cur))
                    cur = [w]
                    cur_tokens = wt
                else:
                    cur.append(w)
                    cur_tokens += wt
            if cur:
                final_chunks.append(" ".join(cur))

    return final_chunks


