import re
from typing import Dict, Any, Tuple
from .nlp_normalizer import normalize_command

INTENTS = [
    "open_app",
    "open_path",
    "create_file",
    "create_folder",
    "delete",
    "set_timer",
    "cancel_timer",
    "enter_prime",
    "exit_prime",
    "unknown",
]

APP_KEYWORDS = [
    "chrome",
    "google chrome",
    "edge",
    "microsoft edge",
    "notepad",
    "vscode",
    "visual studio code",
    "explorer",
]

LOCATION_KEYWORDS = [
    "desktop",
    "downloads",
    "documents",
    "pictures",
    "music",
    "videos",
]


def normalize_text(text: str) -> str:
    return normalize_command(text)


def detect_intent(text: str) -> Tuple[str, float]:
    if "enter prime" in text or "go prime" in text or "go to prime" in text:
        return "enter_prime", 0.95
    if "exit prime" in text or "leave prime" in text or "back to user" in text:
        return "exit_prime", 0.95

    if "cancel timer" in text or "stop timer" in text:
        return "cancel_timer", 0.9

    if "timer" in text or re.search(r"\b\d+\s*(seconds?|minutes?|hours?)\b", text):
        return "set_timer", 0.85

    if any(w in text for w in ["delete", "remove", "erase", "trash"]):
        return "delete", 0.9

    if any(w in text for w in ["create", "make", "new"]):
        if "folder" in text or "directory" in text:
            return "create_folder", 0.9
        if "file" in text or "text file" in text:
            return "create_file", 0.9

    if text.startswith("open ") or text.startswith("launch ") or text.startswith("start "):
        for app in APP_KEYWORDS:
            if app in text:
                return "open_app", 0.9
        return "open_path", 0.7

    if "open" in text:
        for app in APP_KEYWORDS:
            if app in text:
                return "open_app", 0.7

    return "unknown", 0.3


def extract_timer(text: str) -> Dict[str, Any]:
    m = re.search(r"\b(\d+)\s*(seconds?|minutes?|hours?)\b", text)
    if not m:
        return {"timer_value": None, "timer_unit": None}
    value = int(m.group(1))
    unit = m.group(2)
    return {"timer_value": value, "timer_unit": unit}


def extract_location(text: str) -> Dict[str, Any]:
    location = None
    folder_name = None
    m = re.search(r"\b(in|on|at)\s+([a-z0-9 _\\\/:.-]+)", text)
    if m:
        tail = m.group(2).strip()
        parts = tail.split()
        if parts:
            if parts[0] in LOCATION_KEYWORDS:
                location = parts[0]
                if len(parts) > 1:
                    folder_name = " ".join(parts[1:])
            else:
                folder_name = " ".join(parts)
    return {"location": location, "folder_name": folder_name}


def extract_file_name(text: str) -> Dict[str, Any]:
    file_name = None
    file_extension = None

    m_named = re.search(r"\b(named|called)\s+([a-z0-9_. -]+)", text)
    if m_named:
        candidate = m_named.group(2).strip()
        if "." in candidate:
            file_name, file_extension = candidate.rsplit(".", 1)
        else:
            file_name = candidate
    else:
        m_file = re.search(r"\bfile\b\s+([a-z0-9_. -]+)", text)
        if m_file:
            candidate = m_file.group(1).strip()
            stop_words = ["in", "on", "at", "to"]
            tokens = candidate.split()
            cleaned = []
            for t in tokens:
                if t in stop_words:
                    break
                cleaned.append(t)
            candidate = " ".join(cleaned)
            if "." in candidate:
                file_name, file_extension = candidate.rsplit(".", 1)
            else:
                file_name = candidate

    if file_name == "":
        file_name = None

    if file_extension is None and "text file" in text:
        file_extension = "txt"

    return {"file_name": file_name, "file_extension": file_extension}


def extract_app_name(text: str) -> Dict[str, Any]:
    app_name = None
    m = re.search(r"\b(open|launch|start)\s+([a-z0-9 .]+)", text)
    if m:
        candidate = m.group(2).strip()
        candidate = re.split(r"\b(on|in|at)\b", candidate)[0].strip()
        app_name = candidate
    for app in APP_KEYWORDS:
        if app in text:
            app_name = app
            break
    return {"app_name": app_name}


def build_path(location: str, folder_name: str) -> str:
    if location and folder_name:
        return f"{location}/{folder_name}"
    if location:
        return location
    if folder_name:
        return folder_name
    return ""


def extract_entities(text: str, intent: str) -> Dict[str, Any]:
    entities: Dict[str, Any] = {
        "file_name": None,
        "file_extension": None,
        "folder_name": None,
        "location": None,
        "path": None,
        "app_name": None,
        "mode": None,
        "timer_value": None,
        "timer_unit": None,
    }

    if intent in ["create_file", "delete"]:
        entities.update(extract_file_name(text))
        loc = extract_location(text)
        entities.update(loc)
        entities["path"] = build_path(entities["location"], entities["folder_name"])

    elif intent == "create_folder":
        loc = extract_location(text)
        entities.update(loc)
        if entities["folder_name"] is None:
            m = re.search(r"\bfolder\b\s+([a-z0-9_. -]+)", text)
            if m:
                candidate = m.group(1).strip()
                tokens = candidate.split()
                cleaned = []
                for t in tokens:
                    if t in ["in", "on", "at", "to"]:
                        break
                    cleaned.append(t)
                entities["folder_name"] = " ".join(cleaned)
        entities["path"] = build_path(entities["location"], entities["folder_name"])

    elif intent == "open_app":
        entities.update(extract_app_name(text))

    elif intent == "open_path":
        loc = extract_location(text)
        entities.update(loc)
        entities["path"] = build_path(entities["location"], entities["folder_name"])

    elif intent in ["set_timer", "cancel_timer"]:
        timer = extract_timer(text)
        entities.update(timer)

    if intent == "enter_prime":
        entities["mode"] = "PRIME"
    elif intent == "exit_prime":
        entities["mode"] = "USER"

    return entities


def understand_command(text: str) -> Dict[str, Any]:
    normalized = normalize_text(text)
    intent, score = detect_intent(normalized)
    entities = extract_entities(normalized, intent)
    return {
        "raw_text": text,
        "normalized_text": normalized,
        "intent": intent,
        "confidence": score,
        "entities": entities,
    }
