from typing import Iterable, List


def chunk_text(text: str, max_tokens: int = 400) -> List[str]:
    """Simple chunker by sentences; placeholder if pre-chunking is needed."""
    sentences = text.split(". ")
    chunks: List[str] = []
    current = []
    count = 0
    for s in sentences:
        tokens = len(s.split())
        if count + tokens > max_tokens and current:
            chunks.append(". ".join(current).strip())
            current = [s]
            count = tokens
        else:
            current.append(s)
            count += tokens
    if current:
        chunks.append(". ".join(current).strip())
    return chunks


def join_context(chunks: Iterable[str]) -> str:
    return "\n\n".join(chunks)
