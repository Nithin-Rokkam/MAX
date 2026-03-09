import re
from .nlp_normalizer import normalize_command

class ParsedCommand:
    def __init__(self, intent: str, entities: dict | None = None):
        self.intent = intent
        self.entities = entities or {}
        self.last_links = []


class CommandParser:
    def parse(self, text: str) -> ParsedCommand:
        normalized = normalize_command(text)
        t = normalized.strip()

        if not t:
            return ParsedCommand(intent="EMPTY")

        entities = {}
        browser = None   # ✅ REQUIRED DEFAULT
        BROWSERS = ["chrome", "brave", "edge"]


        lowered = t.lower()   # ✅ DEFINE IT HERE ONCE

        for b in BROWSERS:
            pattern = f"in {b}"
            if pattern in lowered:
                browser = b
                t = t.replace(pattern, "").strip()
                lowered = t.lower()
                break

        if browser:
            entities["browser"] = browser



        location, cleaned_text = self._extract_location(lowered, t)
        lowered_clean = cleaned_text.lower()
        
        if text.strip() == "search":
            return ParsedCommand(
                intent="START_SEARCH",
                entities={}
            )

        if text.startswith("search"):
            query = text.replace("search", "").replace("for", "").strip()
            return ParsedCommand(
                intent="SEARCH_QUERY",
                entities={
                    "query": query,
                    "browser": browser
                }
            )
            
        if text.startswith("open") and "search" in text:
            parts = text.split("search", 1)
            target = parts[0].replace("open", "").strip()
            query = parts[1].strip()

            return ParsedCommand(
                intent="OPEN_AND_SEARCH",
                entities={
                    "target": target,
                    "query": query,
                    "browser": browser,
                    "engine": "youtube" if "youtube" in target else None,
                    "new_tab": False
                }
            )


        # ===============================
        # 🔴 HARD RULE: search → WEB_SEARCH
        # ===============================
        if lowered_clean.startswith("search"):
            # strip leading "search"
            query = lowered_clean.replace("search", "", 1).strip()
            # optionally strip leading "for"
            if query.startswith("for"):
                query = query.replace("for", "", 1).strip()

            return ParsedCommand(
                intent="WEB_SEARCH",
                entities={
                    "engine": None,
                    "query": query,
                },
            )

        # ---------- CHAINED YOUTUBE COMMANDS ----------
        # "open youtube and search for X"
        if lowered_clean.startswith("open youtube and search for "):
            q = cleaned_text[len("open youtube and search for "):].strip()
            return ParsedCommand(
                intent="WEB_SEARCH",
                entities={"engine": "youtube", "query": q}
            )

        # "open youtube and play X" -> treat as open+search on youtube
        m2 = re.match(r"^open\s+(.+?)\s+and\s+(?:play|search|play for)\s+(.+)$", lowered_clean, flags=re.I)
        if m2:
            app_part = m2.group(1).strip()
            query_part = m2.group(2).strip()
            engine = None
            if "youtube" in app_part or "yt" in app_part:
                engine = "youtube"
            return ParsedCommand(
                intent="OPEN_AND_SEARCH",
                entities={"target": app_part, "query": query_part, "engine": engine, "new_tab": False}
            )

        # "open youtube and play X" -> for now, treat as youtube search for X
        if lowered_clean.startswith("open youtube and play "):
            q = cleaned_text[len("open youtube and play "):].strip()
            return ParsedCommand(
                intent="WEB_SEARCH",
                entities={"engine": "youtube", "query": q}
            )

        # ---------- SEARCH / START SEARCH ----------
        # handle explicit "search" start (conversational)
        # NOTE: this path is now shadowed by the hard rule above; keep only if you later
        # split WEB_SEARCH vs START_SEARCH by context.

        if lowered_clean == "search":
            return ParsedCommand(intent="START_SEARCH", entities={"engine": None, "browser": "chrome", "new_tab": False})

        # "search in chrome" (start conversational search in Chrome)
        m = re.match(r"^search\s+(?:in|on)\s+([a-z0-9 ]+)$", lowered_clean, flags=re.I)
        if m:
            browser = m.group(1).strip()
            return ParsedCommand(intent="START_SEARCH", entities={"engine": None, "browser": browser, "new_tab": False})

        # Inline search: "search for X", "search X", "google X"
        if lowered_clean.startswith("search for "):
            q = cleaned_text[len("search for "):].strip()
            return ParsedCommand(intent="IN_APP_SEARCH", entities={"engine": None, "query": q, "new_tab": False})

        if lowered_clean.startswith("search "):
            q = cleaned_text[len("search "):].strip()
            if q:
                return ParsedCommand(intent="IN_APP_SEARCH", entities={"engine": None, "query": q, "new_tab": False})

        if lowered_clean.startswith("google "):
            q = cleaned_text[len("google "):].strip()
            return ParsedCommand(intent="IN_APP_SEARCH", entities={"engine": "google", "query": q, "new_tab": False})

        # ---------- OPEN + SEARCH chained command ----------
        m = re.match(r"^open\s+(.+?)\s+and\s+(?:search|search for)\s+(.+)$", lowered_clean, flags=re.I)
        if m:
            app_part = m.group(1).strip()
            query_part = m.group(2).strip()
            engine = None
            if "youtube" in app_part or "yt" in app_part:
                engine = "youtube"
            return ParsedCommand(
                intent="OPEN_AND_SEARCH",
                entities={"target": app_part, "query": query_part, "engine": engine, "new_tab": False}
            )

        # ---------- PLAY / OPEN N-TH ITEM ----------
        if lowered_clean.startswith("open ") or lowered_clean.startswith("play "):
            idx = self._extract_index(lowered_clean)
            if idx is not None:
                return ParsedCommand(
                    intent="PLAY_NTH_VIDEO",
                    entities={"index": idx}
                )

        # ---------- single token as OPEN ----------
        if lowered_clean in ("chrome", "youtube", "edge", "brave", "whatsapp", "comet", "notepad", "explorer", "leetcode"):
            return ParsedCommand(intent="OPEN_APP_OR_FOLDER", entities={"target": cleaned_text, "location": location})

        # ---------- SEARCH LOGIC ----------
        if lowered_clean.startswith("search youtube for "):
            q = cleaned_text[len("search youtube for "):].strip()
            new_tab = False
            lc_q = q.lower()
            if lc_q.endswith(" in new tab"):
                new_tab = True
                q = q[:-len(" in new tab")].strip()
            return ParsedCommand(
                intent="IN_APP_SEARCH",
                entities={"engine": "youtube", "query": q, "new_tab": new_tab}
            )

        if lowered_clean.startswith("search web for "):
            q = cleaned_text[len("search web for "):].strip()
            return ParsedCommand(
                intent="WEB_SEARCH",
                entities={"engine": "google", "query": q}
            )

        if lowered_clean.startswith("google "):
            q = cleaned_text[len("google "):].strip()
            return ParsedCommand(
                intent="WEB_SEARCH",
                entities={"engine": "google", "query": q}
            )

        if lowered_clean.startswith("search for "):
            q = cleaned_text[len("search for "):].strip()
            new_tab = False
            lc_q = q.lower()

            if lc_q.endswith(" in new tab"):
                new_tab = True
                q = q[:-len(" in new tab")].strip()
                lc_q = q.lower()
            elif lc_q.endswith(" in another tab"):
                new_tab = True
                q = q[:-len(" in another tab")].strip()
                lc_q = q.lower()

            engine = None

            if lc_q.endswith(" in youtube") or lc_q.endswith(" on youtube"):
                engine = "youtube"
                q = re.sub(r"\s+(in|on)\s+youtube$", "", q, flags=re.I).strip()
            elif lc_q.endswith(" on web") or lc_q.endswith(" on google"):
                engine = "google"
                q = re.sub(r"\s+on\s+(web|google)$", "", q, flags=re.I).strip()

            return ParsedCommand(
                intent="IN_APP_SEARCH",
                entities={"engine": engine, "query": q, "new_tab": new_tab}
            )

        # ---------- OPEN ----------
        if lowered_clean.startswith("open "):
            name = cleaned_text[5:].strip()
            lc_name = name.lower()

            if lc_name.endswith(" in new tab"):
                name = name[:-len(" in new tab")].strip()
            elif lc_name.endswith(" in another tab"):
                name = name[:-len(" in another tab")].strip()

            return ParsedCommand(
                intent="OPEN_APP_OR_FOLDER",
                entities={"target": name, "location": location}
            )
            
        # ------------ Control cmds --------------
        if "mute" in lowered and "volume" in lowered:
            return ParsedCommand(intent="MUTE_VOLUME")

        if "unmute" in lowered and "volume" in lowered:
            return ParsedCommand(intent="UNMUTE_VOLUME")

        # "increase/raise/turn up volume [to N | by N]"
        if re.search(r"\b(increase|raise|turn up|volume up)\b", lowered) and "volume" in lowered:
            m_to = re.search(r"\bto\s+(\d+)\b", lowered)
            if m_to:
                return ParsedCommand(intent="SET_VOLUME", entities={"level": int(m_to.group(1))})
            m_by = re.search(r"\bby\s+(\d+)\b", lowered)
            amount = int(m_by.group(1)) if m_by else 10
            return ParsedCommand(intent="VOLUME_UP", entities={"amount": amount})

        # "decrease/lower/turn down volume [to N | by N]"
        if re.search(r"\b(decrease|lower|turn down|volume down|reduce)\b", lowered) and "volume" in lowered:
            m_to = re.search(r"\bto\s+(\d+)\b", lowered)
            if m_to:
                return ParsedCommand(intent="SET_VOLUME", entities={"level": int(m_to.group(1))})
            m_by = re.search(r"\bby\s+(\d+)\b", lowered)
            amount = int(m_by.group(1)) if m_by else 10
            return ParsedCommand(intent="VOLUME_DOWN", entities={"amount": amount})

        if "set volume to" in lowered:
            nums = re.findall(r"\d+", lowered)
            if nums:
                level = int(nums[0])
                return ParsedCommand(intent="SET_VOLUME", entities={"level": level})


        # ------------ Brightness cmds --------------
        # "set brightness to 50"
        if "set brightness to" in lowered:
            nums = re.findall(r"\d+", lowered)
            if nums:
                level = int(nums[0])
                return ParsedCommand(intent="SET_BRIGHTNESS", entities={"level": level})

        # "increase/raise brightness to N" → SET (direct)
        # "increase/raise brightness by N" → relative UP
        # "increase/raise brightness"      → relative UP by default 10
        if re.search(r"\b(increase|raise|turn up|brightness up)\b", lowered) and "brightness" in lowered:
            # Check for "to N" first → treat as SET
            m_to = re.search(r"\bto\s+(\d+)\b", lowered)
            if m_to:
                return ParsedCommand(intent="SET_BRIGHTNESS", entities={"level": int(m_to.group(1))})
            # Check for "by N" → relative
            m_by = re.search(r"\bby\s+(\d+)\b", lowered)
            amount = int(m_by.group(1)) if m_by else 10
            return ParsedCommand(intent="BRIGHTNESS_UP", entities={"amount": amount})

        # "decrease/lower/dim brightness to N" → SET (direct)
        # "decrease/lower/dim brightness by N" → relative DOWN
        if re.search(r"\b(decrease|lower|turn down|brightness down|reduce|dim)\b", lowered) and "brightness" in lowered:
            m_to = re.search(r"\bto\s+(\d+)\b", lowered)
            if m_to:
                return ParsedCommand(intent="SET_BRIGHTNESS", entities={"level": int(m_to.group(1))})
            m_by = re.search(r"\bby\s+(\d+)\b", lowered)
            amount = int(m_by.group(1)) if m_by else 10
            return ParsedCommand(intent="BRIGHTNESS_DOWN", entities={"amount": amount})

        # ---------- PASSCODE / MODES ----------
        if lowered_clean.startswith("set passphrase "):
            phrase = cleaned_text[len("set passphrase "):].strip()
            return ParsedCommand(intent="SET_PASSPHRASE", entities={"phrase": phrase})

        if lowered_clean == "enter prime" or lowered_clean == "enter prime mode":
            return ParsedCommand(intent="AUTH_PRIME", entities={})

        if lowered_clean.startswith("enter prime "):
            phrase = cleaned_text[len("enter prime "):].strip()
            return ParsedCommand(intent="AUTH_PRIME", entities={"phrase": phrase})

        if lowered_clean in ("exit prime", "switch to user mode", "user mode"):
            return ParsedCommand(intent="EXIT_PRIME")

        # ---------- OPTIONAL ROOT ----------
        if lowered_clean.startswith("set root "):
            path = cleaned_text[len("set root "):].strip()
            return ParsedCommand(intent="SET_ROOT", entities={"path": path})

        # ---------- CREATE FILE / FOLDER (unified, flexible) ----------
        create_result = self._parse_create(lowered_clean, cleaned_text, location)
        if create_result:
            return create_result

        # ---------- DELETE ----------
        if lowered_clean.startswith("delete "):
            rest = cleaned_text[len("delete "):].strip()
            # Strip leading "folder " or "file " so "delete folder sriram" → "sriram"
            rest_lower = rest.lower()
            if rest_lower.startswith("folder "):
                rest = rest[len("folder "):].strip()
            elif rest_lower.startswith("file "):
                rest = rest[len("file "):].strip()
            name = self._extract_name_with_folder(rest)
            return ParsedCommand(
                intent="DELETE_FILE",
                entities={"path": name, "location": location}
            )

        # ---------- TIMER / SCHEDULED ACTIONS ----------
        # Pattern: "<action> after <delay>" or "<action> in <delay>"
        scheduled = self._parse_scheduled_action(lowered_clean)
        if scheduled:
            return ParsedCommand(
                intent="SCHEDULE_ACTION",
                entities=scheduled
            )

        if lowered_clean.startswith("notify me after "):
            delay_part = lowered_clean[len("notify me after "):].strip()
            delay_sec = self._parse_delay_to_seconds(delay_part)
            return ParsedCommand(
                intent="SET_TIMER",
                entities={"delay_seconds": delay_sec}
            )

        # ---------- LOCK / UNLOCK SCREEN ----------
        if lowered_clean in (
            "lock screen", "lock the screen", "lock system",
            "lock computer", "lock my computer", "lock pc",
            "lock my pc",
        ):
            return ParsedCommand(intent="LOCK_SCREEN")

        if lowered_clean in (
            "unlock screen", "unlock the screen", "unlock system",
            "unlock computer", "unlock",
        ):
            return ParsedCommand(intent="UNLOCK_SCREEN")

        # ---------- SYSTEM ACTIONS ----------
        if lowered_clean in ("shut down", "shutdown", "power off", "shut down now", "shutdown now"):
            return ParsedCommand(intent="SCHEDULE_ACTION", entities={"action": "SHUTDOWN", "delay_seconds": 0})

        if lowered_clean in ("restart", "reboot", "restart now", "reboot now"):
            return ParsedCommand(intent="SCHEDULE_ACTION", entities={"action": "RESTART", "delay_seconds": 0})

        if lowered_clean in ("sleep", "put to sleep", "sleep mode"):
            return ParsedCommand(intent="SCHEDULE_ACTION", entities={"action": "SLEEP", "delay_seconds": 0})



        # ---------- BROWSER TAB CONTROL ----------
        # "close youtube in chrome" / "close github tab"
        tab_close = self._parse_close_tab(lowered_clean, cleaned_text)
        if tab_close:
            return tab_close

        # "open new tab" / "open new tab in chrome"
        if re.match(r"^open\s+(?:a\s+)?new\s+tab(?:\s+in\s+(\w+))?$", lowered_clean):
            m = re.match(r"^open\s+(?:a\s+)?new\s+tab(?:\s+in\s+(\w+))?$", lowered_clean)
            browser = m.group(1) if m.group(1) else None
            return ParsedCommand(intent="NEW_TAB", entities={"browser": browser})

        # "close tab" / "close current tab" / "close this tab"
        if lowered_clean in ("close tab", "close current tab", "close this tab"):
            return ParsedCommand(intent="CLOSE_CURRENT_TAB", entities={})

        # "next tab" / "switch to next tab"
        if lowered_clean in ("next tab", "switch to next tab", "switch tab", "go to next tab"):
            return ParsedCommand(intent="SWITCH_TAB", entities={"direction": "next"})

        # "previous tab" / "switch to previous tab"
        if lowered_clean in ("previous tab", "switch to previous tab",
                             "go to previous tab", "prev tab", "last tab"):
            return ParsedCommand(intent="SWITCH_TAB", entities={"direction": "prev"})

        # ---------- CLOSE APP ----------
        if lowered_clean.startswith("close "):
            name = cleaned_text[len("close "):].strip()
            return ParsedCommand(
                intent="CLOSE_APP_OR_FOLDER",
                entities={"target": name}
            )

        # ---------- Take a Note ----------
        if lowered.startswith(("note", "take a note", "save note", "add note")):
            content = lowered
            for prefix in ["take a note", "save note", "add note", "note that", "note"]:
                if content.startswith(prefix):
                    content = content.replace(prefix, "", 1).strip()
                    break

            return ParsedCommand(
                intent="ADD_NOTE",
                entities={"content": content}
            )
        
        if lowered.startswith("add a note") or lowered.startswith("note"):
            content = lowered.replace("add a note", "").replace("note", "").strip()
            return ParsedCommand(
                intent="ADD_NOTE",
                entities={"content": content}
            )
            
        if lowered in ("show my notes", "read my notes", "open notes", "show notes"):
            return ParsedCommand(intent="READ_NOTES")

        # ---------- VOICE ENROLLMENT ----------
        if any(lowered_clean.startswith(p) for p in (
            "enroll my voice", "enroll voice", "train my voice",
            "setup voice", "set up voice", "register my voice",
        )):
            return ParsedCommand(intent="ENROLL_VOICE")

        if lowered_clean in ("voice status", "check voice", "is voice active",
                             "voice profile status"):
            return ParsedCommand(intent="VOICE_STATUS")

        # ---------- CDII: Cross-Desktop Control ----------
        # "pause YouTube on Desktop 3"  /  "play music on Desktop 2"
        cdii = self._parse_cdii_control(lowered_clean)
        if cdii:
            return ParsedCommand(intent="CDII_CONTROL", entities=cdii)

        # "what's running on Desktop 2" / "list apps on Desktop 1"
        cdii_list = self._parse_cdii_list(lowered_clean)
        if cdii_list is not None:
            return ParsedCommand(intent="CDII_LIST", entities={"desktop_num": cdii_list})

        # ---------- EVENT-BASED AUTOMATION ----------
        # "shut down after this video ends"  /  "notify me when download finishes"
        event_action = self._parse_event_action(lowered_clean)
        if event_action:
            return ParsedCommand(intent="EVENT_ACTION", entities=event_action)

        # ---------- CHAINED AUTOMATION ----------
        # "open chrome and then open notepad" / "open youtube then search for python"
        chain = self._parse_task_chain(text)
        if chain:
            return ParsedCommand(intent="TASK_CHAIN", entities={"steps": chain})

        # ---------- EXIT ----------
        if lowered_clean in ("exit", "quit", "bye"):
            return ParsedCommand(intent="EXIT")


        return ParsedCommand(intent="UNKNOWN", entities={"raw": text})


    # ========== helpers ==========

    def _extract_location(self, lowered: str, original: str):
        location = None
        cleaned = original

        patterns = [
            (" on desktop", "DESKTOP"),
            (" in desktop", "DESKTOP"),
            (" inside desktop", "DESKTOP"),

            (" on documents", "DOCUMENTS"),
            (" in documents", "DOCUMENTS"),
            (" inside documents", "DOCUMENTS"),

            (" on downloads", "DOWNLOADS"),
            (" in downloads", "DOWNLOADS"),
            (" inside downloads", "DOWNLOADS"),
        ]

        for pattern, loc in patterns:
            idx = lowered.rfind(pattern)
            if idx != -1:
                location = loc
                cleaned = original[:idx].strip()
                break

        return location, cleaned

    def _parse_create(self, lowered: str, original: str, location: str | None):
        """
        Unified create parser. Handles all these patterns (and more):
          create a textfile test2 in test in desktop
          create text file report
          create a python file main
          create file notes.md on desktop
          create folder Projects on desktop
          create a docx file report in work
          create a pdf report
          create an excel sheet budget in documents
          create wordfile summary
          make a folder test on desktop
          make a textfile hello in downloads
        Returns ParsedCommand or None.
        """
        # Must start with "create" or "make" or "new"
        m = re.match(r"^(?:create|make|new)\s+(?:a\s+|an\s+)?(.+)$", lowered)
        if not m:
            return None

        rest = m.group(1).strip()
        original_rest = original[len(original) - len(rest):]  # preserve case

        # --- FILE TYPE KEYWORDS → extension mapping ---
        file_type_map = {
            # text files
            "text file": ".txt", "textfile": ".txt", "txt file": ".txt",
            "txt": ".txt", "text": ".txt",
            # documents
            "word file": ".docx", "wordfile": ".docx", "word document": ".docx",
            "docx file": ".docx", "docx": ".docx", "doc file": ".doc",
            "doc": ".doc",
            # spreadsheets
            "excel file": ".xlsx", "excelfile": ".xlsx", "excel sheet": ".xlsx",
            "spreadsheet": ".xlsx", "xlsx file": ".xlsx", "xlsx": ".xlsx",
            "csv file": ".csv", "csv": ".csv",
            # presentations
            "ppt file": ".pptx", "pptx file": ".pptx", "ppt": ".pptx",
            "powerpoint file": ".pptx", "powerpoint": ".pptx",
            "presentation": ".pptx",
            # code files
            "python file": ".py", "py file": ".py",
            "java file": ".java", "javascript file": ".js", "js file": ".js",
            "html file": ".html", "css file": ".css",
            "c file": ".c", "cpp file": ".cpp", "c++ file": ".cpp",
            "json file": ".json", "xml file": ".xml",
            # other
            "pdf file": ".pdf", "pdf": ".pdf",
            "markdown file": ".md", "md file": ".md",
            "log file": ".log",
            "image file": ".png", "photo file": ".png",
        }

        # --- FOLDER KEYWORDS ---
        folder_keywords = ("folder", "directory", "dir")

        # Check if it's a folder creation
        is_folder = False
        folder_name_rest = rest
        for fk in folder_keywords:
            if rest.startswith(fk + " "):
                is_folder = True
                folder_name_rest = rest[len(fk) + 1:].strip()
                break
            elif rest == fk:
                is_folder = True
                folder_name_rest = ""
                break

        if is_folder:
            if not folder_name_rest:
                folder_name_rest = "new_folder"
            name = self._extract_name_with_folder(folder_name_rest)
            return ParsedCommand(
                intent="CREATE_FOLDER",
                entities={"name": name, "location": location}
            )

        # Check for file type keywords (longest match first)
        detected_ext = None
        remaining = rest
        sorted_types = sorted(file_type_map.keys(), key=len, reverse=True)
        for type_kw in sorted_types:
            # Match type keyword at start: "textfile test2" or "python file main"
            if remaining.startswith(type_kw + " "):
                detected_ext = file_type_map[type_kw]
                remaining = remaining[len(type_kw):].strip()
                break
            elif remaining.startswith(type_kw):
                detected_ext = file_type_map[type_kw]
                remaining = remaining[len(type_kw):].strip()
                break
            # Match "file <name>" pattern with type as qualifier: "<type> <name>"
            # Also handle "file" appearing after type: "docx file report"
            pattern = type_kw.replace(" ", r"\s+")
            tm = re.match(rf"^{pattern}\s*(.*)$", remaining)
            if tm:
                detected_ext = file_type_map[type_kw]
                remaining = tm.group(1).strip()
                break

        # If no file type keyword matched, check for generic "file" prefix
        if detected_ext is None:
            if remaining.startswith("file "):
                remaining = remaining[len("file "):].strip()
            elif remaining == "file":
                remaining = ""

        # Parse nested path from remaining: "test2 in test" → "test/test2"
        name = self._extract_name_with_folder(remaining) if remaining else "newfile"

        # Add extension if needed
        if detected_ext:
            # Only add extension if name doesn't already have one
            if "." not in name.split("/")[-1]:
                name = name + detected_ext
            is_text = detected_ext == ".txt"
        else:
            # Generic file — default to .txt if no extension present
            if "." not in name.split("/")[-1]:
                name = name + ".txt"
                is_text = True
            else:
                is_text = name.lower().endswith(".txt")

        return ParsedCommand(
            intent="CREATE_FILE",
            entities={"name": name, "text_default": is_text, "location": location}
        )

    def _parse_create_file_rest(self, rest: str, default_name: str, default_text: bool) -> str:
        base = rest.strip()
        lower_base = base.lower()

        # "in folder test" / "inside folder test" (no explicit filename)
        if lower_base.startswith("in folder "):
            folder = base[len("in folder "):].strip()
            if not folder:
                return default_name
            return f"{folder}/{default_name}"

        if lower_base.startswith("inside folder "):
            folder = base[len("inside folder "):].strip()
            if not folder:
                return default_name
            return f"{folder}/{default_name}"

        name_with_folder = self._extract_name_with_folder(base)
        return name_with_folder

    def _extract_name_with_folder(self, rest: str) -> str:
        """
        Examples:
        - 'notes'                   -> 'notes'
        - 'notes in xyz'            -> 'xyz/notes'
        - 'notes in xyz folder'     -> 'xyz/notes'
        - 'notes in folder xyz'     -> 'xyz/notes'
        - 'notes inside xyz'        -> 'xyz/notes'
        - 'notes inside folder xyz' -> 'xyz/notes'
        """
        base = rest.strip()
        lower_base = base.lower()

        # treat "inside" as "in"
        lower_base = lower_base.replace(" inside ", " in ")
        base = base.replace(" inside ", " in ")

        idx = lower_base.rfind(" in ")
        if idx == -1:
            return base

        first_part = base[:idx].strip()
        second_part = base[idx + 4:].strip()

        if second_part.lower().endswith(" folder"):
            second_part = second_part[:-len(" folder")].strip()

        if second_part.lower().startswith("folder "):
            second_part = second_part[len("folder "):].strip()

        if not second_part:
            return first_part

        return f"{second_part}/{first_part}"

    def _parse_delay_to_seconds(self, s: str) -> int:
        parts = s.split()
        if not parts:
            return 0

        try:
            value = int(parts[0])
        except ValueError:
            return 0

        if len(parts) == 1:
            return value

        unit = parts[1]
        if unit.startswith("sec"):
            return value
        if unit.startswith("min"):
            return value * 60
        if unit.startswith("hour"):
            return value * 3600

        return value

    def _parse_scheduled_action(self, text: str) -> dict | None:
        """
        Parses patterns like:
          'shut down after 20 minutes'
          'shutdown in 10 minutes'
          'lock after 5 minutes'
          'restart in 1 hour'
          'sleep after 30 seconds'
        Returns {action, delay_seconds} or None.
        """
        action_map = {
            "shut down": "SHUTDOWN",
            "shutdown": "SHUTDOWN",
            "power off": "SHUTDOWN",
            "turn off": "SHUTDOWN",
            "restart": "RESTART",
            "reboot": "RESTART",
            "lock": "LOCK",
            "lock screen": "LOCK",
            "lock the screen": "LOCK",
            "lock system": "LOCK",
            "sleep": "SLEEP",
            "put to sleep": "SLEEP",
            "hibernate": "SLEEP",
        }

        # Pattern: "<action> after/in <delay>"
        pattern = r'^(.+?)\s+(?:after|in)\s+(\d+)\s*(second|seconds|sec|minute|minutes|min|hour|hours|hr)$'
        m = re.match(pattern, text.strip(), flags=re.I)
        if not m:
            return None

        action_raw = m.group(1).strip().lower()
        amount = int(m.group(2))
        unit = m.group(3).lower()

        action = None
        for key in sorted(action_map.keys(), key=len, reverse=True):
            if action_raw == key or action_raw.endswith(key):
                action = action_map[key]
                break

        if action is None:
            return None

        if unit.startswith("sec"):
            delay_sec = amount
        elif unit.startswith("min"):
            delay_sec = amount * 60
        else:  # hour
            delay_sec = amount * 3600

        return {"action": action, "delay_seconds": delay_sec}


    def _parse_close_tab(self, lowered: str, original: str):
        """
        Detects tab-close patterns:
          'close youtube in chrome'    → tab_keyword=youtube, browser=chrome
          'close github tab'           → tab_keyword=github, browser=None
          'close youtube tab in brave' → tab_keyword=youtube, browser=brave
          'close the youtube tab'      → tab_keyword=youtube, browser=None
        Returns ParsedCommand or None.
        """
        # Pattern 1: "close <X> in <browser>"
        m = re.match(r"^close\s+(.+?)\s+in\s+(chrome|brave|edge|firefox)$", lowered)
        if m:
            tab_kw = m.group(1).strip()
            browser = m.group(2).strip()
            # Filter out things that look like app names (not tab targets)
            if tab_kw not in ("chrome", "brave", "edge", "firefox", "notepad"):
                return ParsedCommand(
                    intent="CLOSE_TAB",
                    entities={"tab_keyword": tab_kw, "browser": browser}
                )

        # Pattern 2: "close <X> tab [in <browser>]"
        m = re.match(r"^close\s+(?:the\s+)?(.+?)\s+tab(?:\s+in\s+(\w+))?$", lowered)
        if m:
            tab_kw = m.group(1).strip()
            browser = m.group(2).strip() if m.group(2) else None
            return ParsedCommand(
                intent="CLOSE_TAB",
                entities={"tab_keyword": tab_kw, "browser": browser}
            )

        return None

    def _extract_index(self, lowered_clean: str) -> int | None:
        word_to_num = {
            "first": 1,
            "second": 2,
            "third": 3,
            "fourth": 4,
            "fifth": 5,
        }
        for word, num in word_to_num.items():
            if word in lowered_clean:
                return num

        m = re.search(r"\b(\d+)\b", lowered_clean)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return None
        return None

    def _parse_cdii_control(self, text: str) -> dict | None:
        """
        Parses: "<action> <app> on Desktop <N>"
        Examples:
          "pause youtube on desktop 3"
          "play music on desktop 2"
          "close chrome on desktop 1"
        """
        pattern = r'^(.+?)\s+(?:on|in|at)\s+desktop\s+(\d+)$'
        m = re.match(pattern, text.strip(), flags=re.I)
        if not m:
            return None

        action_app = m.group(1).strip()
        desktop_num = int(m.group(2))

        # Try to split into action + app
        # Common actions: pause, play, stop, close, mute, next, previous
        action_words = ("pause", "play", "stop", "close", "mute", "unmute",
                        "next", "previous", "skip", "open", "quit")
        action = None
        app = action_app

        for word in action_words:
            if action_app.startswith(word + " "):
                action = word
                app = action_app[len(word):].strip()
                break
            if action_app == word:
                action = word
                app = ""
                break

        if action is None:
            return None

        return {"action": action, "app": app, "desktop_num": desktop_num}

    def _parse_cdii_list(self, text: str) -> int | None:
        """
        Parses: "what's running on Desktop N" / "list apps on Desktop N"
        Returns desktop_num, or None if not matched.
        """
        patterns = [
            r"(?:what(?:'s|s| is)\s+running|list apps?|show apps?|apps on)\s+(?:on\s+)?desktop\s+(\d+)",
            r"what(?:'s|s| is)\s+on\s+desktop\s+(\d+)",
        ]
        for p in patterns:
            m = re.search(p, text, flags=re.I)
            if m:
                return int(m.group(1))
        return None

    def _parse_event_action(self, text: str) -> dict | None:
        """
        Parses event-based automation:
          "shut down after this video ends"
          "lock after copying completes"
          "notify me when download finishes"
          "shut down after download finishes"
        Returns {trigger, action} or None.
        """
        trigger_map = {
            "video ends":        "VIDEO_END",
            "video finishes":    "VIDEO_END",
            "video stops":       "VIDEO_END",
            "movie ends":        "VIDEO_END",
            "download finishes": "DOWNLOAD_DONE",
            "download completes":"DOWNLOAD_DONE",
            "download is done":  "DOWNLOAD_DONE",
            "copying finishes":  "COPY_DONE",
            "copying completes": "COPY_DONE",
            "copy finishes":     "COPY_DONE",
            "copy completes":    "COPY_DONE",
        }

        action_map = {
            "shut down": "SHUTDOWN",
            "shutdown":  "SHUTDOWN",
            "power off": "SHUTDOWN",
            "restart":   "RESTART",
            "lock":      "LOCK",
            "lock screen":"LOCK",
            "sleep":     "SLEEP",
            "notify":    "NOTIFY",
            "notify me": "NOTIFY",
            "alert me":  "NOTIFY",
            "remind me": "NOTIFY",
        }

        # Pattern: "<action> after/when <trigger>"
        pattern = r'^(.+?)\s+(?:after|when|once|after this|when this)\s+(.+)$'
        m = re.match(pattern, text, flags=re.I)
        if not m:
            return None

        action_raw = m.group(1).strip().lower()
        trigger_raw = m.group(2).strip().lower()

        trigger = None
        for key, val in trigger_map.items():
            if key in trigger_raw:
                trigger = val
                break

        action = None
        for key in sorted(action_map.keys(), key=len, reverse=True):
            if action_raw.endswith(key) or action_raw == key:
                action = action_map[key]
                break

        if trigger is None or action is None:
            return None

        return {"trigger": trigger, "action": action}

    def _parse_task_chain(self, text: str) -> list | None:
        """
        Splits chained commands:
          "open chrome and then open notepad"  → ["open chrome", "open notepad"]
          "open youtube then search for python" → ["open youtube", "search for python"]
        Returns list of sub-command strings, or None if not a chain.
        """
        # Only trigger if multiple distinct commands are implied
        separators = [
            r"\s+and\s+then\s+",
            r"\s+then\s+",
            r"\s+after\s+that\s+",
            r"\s+afterwards\s+",
            r"\s+followed\s+by\s+",
        ]

        for sep in separators:
            parts = re.split(sep, text, flags=re.I)
            if len(parts) >= 2:
                # Ensure each part is non-trivial
                cleaned = [p.strip() for p in parts if p.strip()]
                if len(cleaned) >= 2:
                    return cleaned

        return None
