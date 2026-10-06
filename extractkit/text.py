"""Extract common entities (emails, URLs, phones, dates, money) from plain text using regular expressions."""
import re

PATTERNS = {
    "emails": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "urls": re.compile(r"https?://[^\s<>\"')\]]+"),
    # Loose international/AU/US phone numbers: needs at least 8 digits overall (checked below).
    "phones": re.compile(r"(?<!\w)\+?\(?\d[\d\s().-]{6,}\d(?!\w)"),
    # 2026-10-06, 06/10/2026, 6 Oct 2026, October 6, 2026
    "dates": re.compile(
        r"\b\d{4}-\d{2}-\d{2}\b"
        r"|\b\d{1,2}/\d{1,2}/\d{2,4}\b"
        r"|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b"
        r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
        re.IGNORECASE,
    ),
    "money": re.compile(r"[$€£]\s?\d[\d,]*(?:\.\d{1,2})?"),
    "hashtags": re.compile(r"(?<!\w)#[A-Za-z]\w+"),
}


def extract_entities(text, kinds=None):
    """Return {kind: [unique matches in order of appearance]} for the requested kinds (default: all)."""
    results = {}
    for kind in kinds or PATTERNS:
        seen = {}
        for match in PATTERNS[kind].findall(text):
            value = match.strip().rstrip(".,;:")
            if kind == "phones" and (
                len(re.sub(r"\D", "", value)) < 8 or PATTERNS["dates"].fullmatch(value)
            ):
                continue  # too short to be a phone number, or actually a date
            seen.setdefault(value, None)  # dict keeps order and removes duplicates
        results[kind] = list(seen)
    return results


def word_frequencies(text, top=20, min_length=4):
    """Most common words, ignoring short ones."""
    from collections import Counter
    words = re.findall(r"[A-Za-z']+", text.lower())
    return Counter(w for w in words if len(w) >= min_length).most_common(top)
