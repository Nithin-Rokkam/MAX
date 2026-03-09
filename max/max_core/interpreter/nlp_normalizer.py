import re
from difflib import get_close_matches
from typing import List

ACTION_KEYWORDS = [
    "open",
    "create",
    "make",
    "delete",
    "remove",
    "start",
    "launch",
    "set",
    "cancel",
    "enter",
    "exit",
    "close",
]

OBJECT_KEYWORDS = [
    "file",
    "folder",
    "directory",
    "text",
    "timer",
    "mode",
]

LOCATION_KEYWORDS = [
    "desktop",
    "downloads",
    "documents",
    "pictures",
    "music",
    "videos",
]

# IMPORTANT: keep app keywords as single tokens
APP_KEYWORDS = [
    "chrome",
    "edge",
    "notepad",
    "vscode",
    "explorer",
    "whatsapp",
    "brave",
    "store",
    "comet",
]

MODE_KEYWORDS = [
    "prime",
    "user",
]

TIMER_KEYWORDS = [
    "seconds",
    "second",
    "minutes",
    "minute",
    "hours",
    "hour",
    "timer",
]

FILLER_WORDS = [
    "please",
    "bro",
    "buddy",
    "dude",
    "yaar",
    "can",
    "you",
    "could",
    "would",
    "just",
    "kindly",
    "u",
]

FILLER_PREFIXES = [
    "hey max",
    "hi max",
    "okay max",
    "ok max",
    "hey",
    "hi",
    "max",
    "yo",
]

COMMON_PHRASE_REPLACEMENTS = {
    "note pad": "notepad",
    "desk top": "desktop",
    "gogle": "google",
    "googel": "google",
    "googgle": "google",
    "crome": "chrome",
    "chorme": "chrome",
    "comme": "comet",
    "combat": "comet",
    "commett": "comet",
    "comment": "comet",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "download folder": "downloads",
    "doc uments": "documents",
    "file explorer": "explorer",
    "prime mode": "prime",

    # NEW: handle Edge / Store / WhatsApp phrases early
    "microsoft edge": "edge",
    "ms edge": "edge",
    "edge browser": "edge",
    "microsoft store": "store",
    "windows store": "store",
    "whats app": "whatsapp",
    "what's app": "whatsapp",
    "google chrome": "chrome",
}


def basic_clean(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"\s+", " ", s)
    for wrong, right in COMMON_PHRASE_REPLACEMENTS.items():
        s = re.sub(r"\b" + re.escape(wrong) + r"\b", right, s)
    s = re.sub(r"\s+", " ", s)
    return s


def strip_filler_prefixes(text: str) -> str:
    s = text.strip()
    changed = True
    while changed:
        changed = False
        for prefix in FILLER_PREFIXES:
            pref = prefix + " "
            if s.startswith(pref):
                s = s[len(pref):].strip()
                changed = True
    return s


def remove_filler_words(tokens: List[str]) -> List[str]:
    result = []
    for t in tokens:
        if t in FILLER_WORDS:
            continue
        result.append(t)
    return result


def _fuzzy_in_list(token: str, vocab: List[str], cutoff: float = 0.9) -> str:
    """
    Stricter fuzzy match: only correct when very close.
    This prevents 'comet' -> 'chrome' type mistakes.
    """
    matches = get_close_matches(token, vocab, n=1, cutoff=cutoff)
    if matches:
        return matches[0]
    return token


def context_fuzzy_tokens(tokens: List[str]) -> List[str]:
    """
    Use context to gently correct obvious typos, but don't over-correct.
    """
    result: List[str] = []
    for i, t in enumerate(tokens):
        if t.isdigit():
            result.append(t)
            continue
        if len(t) <= 2:
            result.append(t)
            continue

        prev = result[i - 1] if i > 0 else ""

        corrected = t

        # First token: likely the action
        if i == 0:
            corrected = _fuzzy_in_list(t, ACTION_KEYWORDS, cutoff=0.8)
        # After 'open/launch/start/close' -> app name
        elif prev in ("open", "launch", "start", "close"):
            corrected = _fuzzy_in_list(t, APP_KEYWORDS, cutoff=0.9)
        # After 'on/in/at' -> location
        elif prev in ("on", "in", "at"):
            corrected = _fuzzy_in_list(t, LOCATION_KEYWORDS, cutoff=0.85)
        # After time-related words -> timer keyword
        elif prev in ("timer", "after", "for"):
            corrected = _fuzzy_in_list(t, TIMER_KEYWORDS, cutoff=0.8)

        result.append(corrected)

    return result


def normalize_command(text: str) -> str:
    s = basic_clean(text)
    s = strip_filler_prefixes(s)
    tokens = s.split()
    tokens = remove_filler_words(tokens)
    tokens = context_fuzzy_tokens(tokens)
    s = " ".join(tokens)
    s = re.sub(r"\s+", " ", s).strip()
    return s
