import os
import re
import time
import json
import shutil
import requests
import webbrowser
import subprocess
from pathlib import Path
from pywinauto import Desktop
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from pywinauto.keyboard import send_keys
from difflib import SequenceMatcher, get_close_matches
from max_core.interpreter.command_parser import ParsedCommand
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


try:
    from pywinauto import Desktop
except ImportError:
    Desktop = None

def similarity(a, b):
    a = a.lower().strip()
    b = b.lower().strip()
    return SequenceMatcher(None, a, b).ratio()



class CommandExecutor:
    def __init__(self, config_manager):
        self.user_home = Path.home()
        self.config = config_manager
        self.last_search_engine = None
        self.last_search_query = None
        self.last_search_url = None
        self.last_search_links = []
        # pending conversational search state:
        # example: {"engine": None, "browser": "chrome", "new_tab": False}
        self.pending_search = None
        self.last_links = []
        self.context = {
            "active_app": None,
            "active_browser": None,
            "last_intent": None,
            "last_search_engine": None,
            "last_search_query": None,
        }

    def execute(self, parsed_command):
        self.context["last_intent"] = parsed_command.intent
        intent = parsed_command.intent

        if intent == "EMPTY":
            return {"done": False, "message": None}

        if intent == "OPEN_APP_OR_FOLDER":
            target = parsed_command.entities.get("target", "")
            location = parsed_command.entities.get("location")
            browser = parsed_command.entities.get("browser")
            return self._handle_open(target, location, browser)
        
        if intent == "WEB_SEARCH":
            engine = parsed_command.entities.get("engine", "google")
            query = parsed_command.entities.get("query", "")
            return self._web_search(engine, query)
        
        if intent == "IN_APP_SEARCH":
            engine = parsed_command.entities.get("engine")
            query = parsed_command.entities.get("query", "")
            new_tab = parsed_command.entities.get("new_tab", False)
            return self._in_app_search(engine, query, new_tab)

        if intent == "PLAY_NTH_VIDEO":
            index = parsed_command.entities.get("index", 1)

            if self.last_search_engine != "youtube":
                return {
                    "done": False,
                    "message": "Play works only after a YouTube search."
                }

            return self._open_nth_youtube(index)

        if intent == "ADD_NOTE":
            content = parsed_command.entities.get("content", "")
            return self._add_note(content)

        
        if intent == "OPEN_AND_SEARCH":
            target = parsed_command.entities.get("target", "")
            query = parsed_command.entities.get("query", "")
            engine = parsed_command.entities.get("engine")
            browser = parsed_command.entities.get("browser")
            new_tab = parsed_command.entities.get("new_tab", False)

            if not target or not query:
                return {"done": False, "message": "Open and search needs both target and query."}

            # Decide engine
            actual_engine = engine or target.lower()

            # Build URL
            if actual_engine == "youtube":
                self.last_search_engine = "youtube"
                self.last_search_query = query
                url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
            else:
                self.last_search_engine = "google"
                self.last_search_query = query
                url = f"https://www.google.com/search?q={quote_plus(query)}"

            self.last_search_url = url

            # Open in specified browser if mentioned
            if browser:
                opened = self._open_url_in_browser(browser, url)
                if opened:
                    return {
                        "done": False,
                        "message": f"Opened {actual_engine} and searched for '{query}' in {browser}."
                    }

            # Fallback: system default browser
            os.startfile(url)
            return {
                "done": False,
                "message": f"Opened {actual_engine} and searched for '{query}'."
            }

        
        if intent == "START_SEARCH":
            # set pending search context and prompt the user
            engine = parsed_command.entities.get("engine")    # may be None
            browser = parsed_command.entities.get("browser")  # e.g., 'chrome'
            new_tab = parsed_command.entities.get("new_tab", False)
            self.pending_search = {"engine": engine, "browser": browser, "new_tab": new_tab}
            return {"done": False, "message": "Ready — what should I search for?"}
        
        if intent == "IN_APP_SEARCH":
            engine = parsed_command.entities.get("engine")
            query = parsed_command.entities.get("query", "")
            new_tab = parsed_command.entities.get("new_tab", False)
            browser = parsed_command.entities.get("browser")
            return self._in_app_search(engine, query, new_tab, browser)

        
        if intent == "SEARCH_QUERY":
            query = parsed_command.entities.get("query", "")
            engine = parsed_command.entities.get("engine")
            return self._in_app_search(engine, query, new_tab=False)


        if intent == "CLOSE_APP_OR_FOLDER":
            target = parsed_command.entities.get("target", "")
            return self._handle_close(target)

        if intent == "CLOSE_TAB":
            tab_kw = parsed_command.entities.get("tab_keyword", "")
            browser = parsed_command.entities.get("browser")
            return self._close_browser_tab(tab_kw, browser)

        if intent == "NEW_TAB":
            browser = parsed_command.entities.get("browser")
            return self._open_new_tab(browser)

        if intent == "CLOSE_CURRENT_TAB":
            return self._close_current_tab()

        if intent == "SWITCH_TAB":
            direction = parsed_command.entities.get("direction", "next")
            return self._switch_tab(direction)

        if intent == "CREATE_FOLDER":
            name = parsed_command.entities.get("name", "")
            location = parsed_command.entities.get("location")
            return self._create_folder(name, location)

        if intent == "CREATE_FILE":
            name = parsed_command.entities.get("name", "")
            text_default = parsed_command.entities.get("text_default", False)
            location = parsed_command.entities.get("location")
            return self._create_file(name, text_default, location)

        if intent == "DELETE_FILE":
            target = parsed_command.entities.get("path", "")
            location = parsed_command.entities.get("location")
            return self._delete_path(target, location)

        if intent == "EXIT":
            return {"done": True, "message": "Shutting down MAX session."}

        if intent == "UNKNOWN":
            raw = parsed_command.entities.get("raw", "")
            return {"done": False, "message": f"I don't understand '{raw}' yet."}
        
        if intent == "MUTE_VOLUME":
            return self._mute_volume()

        if intent == "UNMUTE_VOLUME":
            return self._unmute_volume()

        if intent == "VOLUME_UP":
            amount = parsed_command.entities.get("amount", 10)
            return self._volume_up(amount)

        if intent == "VOLUME_DOWN":
            amount = parsed_command.entities.get("amount", 10)
            return self._volume_down(amount)

        if intent == "SET_VOLUME":
            level = parsed_command.entities.get("level", 50)
            return self._set_volume(level)

        if intent == "SET_BRIGHTNESS":
            level = parsed_command.entities.get("level", 50)
            return self._set_brightness(level)

        if intent == "BRIGHTNESS_UP":
            amount = parsed_command.entities.get("amount", 10)
            return self._brightness_up(amount)

        if intent == "BRIGHTNESS_DOWN":
            amount = parsed_command.entities.get("amount", 10)
            return self._brightness_down(amount)


        return {"done": False, "message": "Unhandled intent."}

    def _get_special_base(self, location):
        if location == "DESKTOP":
            candidate1 = self.user_home / "Desktop"
            candidate2 = self.user_home / "OneDrive" / "Desktop"
            if candidate1.exists():
                return candidate1
            if candidate2.exists():
                return candidate2
            return self.user_home / "Desktop"

        if location == "DOCUMENTS":
            candidate1 = self.user_home / "Documents"
            candidate2 = self.user_home / "OneDrive" / "Documents"
            if candidate1.exists():
                return candidate1
            if candidate2.exists():
                return candidate2
            return self.user_home / "Documents"

        if location == "DOWNLOADS":
            return self.user_home / "Downloads"

        return None

    def _resolve_path(self, name: str, location=None) -> Path:
        path = Path(name).expanduser()
        if path.is_absolute():
            return path

        base = self._get_special_base(location)
        if base is not None:
            return base / path

        root = self.config.get_root_path()
        return root / path

    def _handle_open(self, target: str, location=None, browser: str = None):
        if not target:
            return {"done": False, "message": "Open what?"}

        lowered = target.lower()

        apps = self.config.get_apps()
        for app_id, meta in apps.items():
            aliases = meta.get("aliases") or [app_id]
            for alias in aliases:
                if lowered == alias.lower():
                    app_path = meta.get("path")
                    if app_path:
                        try:
                            subprocess.Popen([app_path])
                            return {"done": False, "message": f"Opened {app_id}."}
                        except Exception as e:
                            return {"done": False, "message": f"Failed to open {app_id}: {e}"}

        if lowered in ("notepad", "note pad"):
            return self._open_notepad()

        if lowered in ("downloads", "download", "download folder"):
            return self._open_downloads()

        if lowered in ("desktop", "desktop folder"):
            return self._open_desktop()

        if lowered in ("documents", "document", "docs", "my documents"):
            return self._open_documents()

        if lowered in ("chrome", "google chrome", "browser"):
            return self._open_chrome()

        if lowered in ("youtube", "yt"):
            self.last_search_engine = "youtube"
            self.active_browser = self._detect_active_browser()
            return self._open_url("https://www.youtube.com/", browser, label="YouTube")



        if "microsoft edge" in lowered or lowered == "edge":
            return self._open_edge()

        if "microsoft store" in lowered or "edge store" in lowered or lowered == "store":
            return self._open_store()

        if lowered in ("brave", "brave browser"):
            return self._open_brave()

        if lowered in ("whatsapp", "whats app", "whatsapp desktop"):
            return self._open_whatsapp()

        if lowered in ("comet",):
            return self._open_comet()
        
        # LeetCode convenience
        if lowered == "leetcode":
            return self._open_url("https://leetcode.com", browser, label="LeetCode")
        
        # Domain-style target: treat as website
        if "." in target and " " not in target:
            url = target
            if not url.startswith("http"):
                url = "https://" + url
            return self._open_url(url, browser)

        candidate = self._resolve_path(target, location)
        if candidate.exists():
            os.startfile(candidate)
            if candidate.is_dir():
                return {"done": False, "message": f"Opened folder '{candidate}'."}
            return {"done": False, "message": f"Opened file '{candidate.name}'."}

        shortcut = self._search_start_menu_shortcut(target)
        if shortcut is not None:
            os.startfile(shortcut)
            return {"done": False, "message": f"Opened '{shortcut.stem}' from Start Menu."}

        # Try semantic / date-based file search ("yesterday's PPT", "latest resume")
        semantic_result = self._semantic_file_search(lowered)
        if semantic_result is not None:
            os.startfile(semantic_result)
            return {"done": False, "message": f"Opened '{semantic_result.name}'."}

        file_or_folder = self._search_file_or_folder_by_name(target, location)
        if file_or_folder is not None:
            os.startfile(file_or_folder)
            if file_or_folder.is_dir():
                return {"done": False, "message": f"Opened folder '{file_or_folder}'."}
            return {"done": False, "message": f"Opened file '{file_or_folder.name}'."}

        return self._open_generic_app(target)



    def _handle_close(self, target: str):
        target = target.lower()

        running_processes = self._get_running_apps()

        best_proc = None
        best_score = 0

        for exe in running_processes:
            clean = exe.replace(".exe", "")
            score = max(
                similarity(target, exe),
                similarity(target, clean),
                similarity(target.replace(" ", ""), clean.replace(" ", "")),
            )
            if score > best_score:
                best_score = score
                best_proc = exe

        if best_proc and best_score >= 0.55:
            try:
                subprocess.run(["taskkill", "/IM", best_proc, "/F"], capture_output=True)
                return {"done": False, "message": f"Closed {best_proc.replace('.exe','')}."}
            except Exception as e:
                return {"done": False, "message": f"Failed to close {best_proc}: {e}"}

        return {"done": False, "message": f"No open windows matching '{target}' found."}

    # ─── BROWSER TAB CONTROL ──────────────────────────────────────────────

    def _close_browser_tab(self, tab_keyword: str, browser: str = None):
        """
        Close a specific browser tab whose title contains `tab_keyword`.
        Works by:
          1. Focusing the browser window
          2. Cycling through tabs (Ctrl+Tab) reading window title
          3. Closing the tab when title contains the keyword (Ctrl+W)
        """
        if not Desktop:
            return {"done": False, "message": "Tab control requires pywinauto."}

        # Map keyword to broader match hints
        kw = tab_keyword.lower().strip()

        # Try to focus the right browser
        browser_targets = {
            "chrome": ["chrome"],
            "brave": ["brave"],
            "edge": ["edge"],
            "firefox": ["firefox", "mozilla"],
        }
        prefer = browser_targets.get(browser, None)

        window = self._focus_any_browser(prefer=prefer)
        if not window:
            return {"done": False, "message": f"Could not find an open browser to close the '{kw}' tab."}

        time.sleep(0.3)

        # Read current window title
        try:
            initial_title = window.window_text() or ""
        except Exception:
            initial_title = ""

        # Check if current tab matches
        if kw in initial_title.lower():
            send_keys("^w")  # Ctrl+W closes current tab
            return {"done": False, "message": f"Closed the '{kw}' tab."}

        # Cycle through tabs to find the matching one
        max_tabs = 30  # safety limit
        for _ in range(max_tabs):
            send_keys("^{TAB}")  # Ctrl+Tab = next tab
            time.sleep(0.4)

            try:
                current_title = window.window_text() or ""
            except Exception:
                current_title = ""

            if kw in current_title.lower():
                send_keys("^w")  # close this tab
                return {"done": False, "message": f"Closed the '{kw}' tab."}

            # If we've cycled back to initial title, stop
            if current_title == initial_title:
                break

        return {"done": False, "message": f"No tab matching '{kw}' found in the browser."}

    def _open_new_tab(self, browser: str = None):
        """Opens a new browser tab (Ctrl+T)."""
        prefer = [browser] if browser else None
        window = self._focus_any_browser(prefer=prefer)
        if not window:
            return {"done": False, "message": "No browser found to open a new tab in."}

        time.sleep(0.2)
        send_keys("^t")  # Ctrl+T
        browser_name = browser or "browser"
        return {"done": False, "message": f"Opened a new tab in {browser_name}."}

    def _close_current_tab(self):
        """Closes the currently active browser tab (Ctrl+W)."""
        window = self._focus_any_browser()
        if not window:
            return {"done": False, "message": "No browser found to close a tab."}

        time.sleep(0.2)
        send_keys("^w")  # Ctrl+W
        return {"done": False, "message": "Closed the current tab."}

    def _switch_tab(self, direction: str = "next"):
        """Switches to the next or previous browser tab."""
        window = self._focus_any_browser()
        if not window:
            return {"done": False, "message": "No browser found to switch tabs."}

        time.sleep(0.2)
        if direction == "prev":
            send_keys("^+{TAB}")  # Ctrl+Shift+Tab = previous tab
            return {"done": False, "message": "Switched to the previous tab."}
        else:
            send_keys("^{TAB}")  # Ctrl+Tab = next tab
            return {"done": False, "message": "Switched to the next tab."}



    def _open_notepad(self):
        try:
            subprocess.Popen(["notepad.exe"])
            return {"done": False, "message": "Opened Notepad."}
        except Exception as e:
            return {"done": False, "message": f"Failed to open Notepad: {e}"}

    def _open_downloads(self):
        folder = self.user_home / "Downloads"
        if folder.exists():
            os.startfile(folder)
            return {"done": False, "message": "Opened Downloads folder."}
        return {"done": False, "message": "Downloads folder not found."}

    def _open_desktop(self):
        candidate1 = self.user_home / "Desktop"
        candidate2 = self.user_home / "OneDrive" / "Desktop"

        if candidate1.exists():
            os.startfile(candidate1)
            return {"done": False, "message": "Opened Desktop folder."}

        if candidate2.exists():
            os.startfile(candidate2)
            return {"done": False, "message": "Opened Desktop folder."}

        return {"done": False, "message": "Desktop folder not found."}

    def _open_documents(self):
        candidate1 = self.user_home / "Documents"
        candidate2 = self.user_home / "OneDrive" / "Documents"

        if candidate1.exists():
            os.startfile(candidate1)
            return {"done": False, "message": "Opened Documents folder."}

        if candidate2.exists():
            os.startfile(candidate2)
            return {"done": False, "message": "Opened Documents folder."}

        return {"done": False, "message": "Documents folder not found."}

    def _open_chrome(self):
        possible_paths = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        ]

        for path in possible_paths:
            if path.exists():
                try:
                    subprocess.Popen([str(path)])
                    return {"done": False, "message": "Opened Chrome."}
                except Exception as e:
                    return {"done": False, "message": f"Failed to open Chrome: {e}"}

        try:
            subprocess.Popen(["chrome"])
            self.active_browser = "chrome"
            self.context["active_browser"] = "chrome"
            return {"done": False, "message": "Tried to open Chrome from PATH."}
        except Exception as e:
            return {"done": False, "message": f"Chrome not found: {e}"}

    def _open_edge(self):
        possible_paths = [
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        ]
        for path in possible_paths:
            if path.exists():
                try:
                    subprocess.Popen([str(path)])
                    return {"done": False, "message": "Opened Microsoft Edge."}
                except Exception as e:
                    return {"done": False, "message": f"Failed to open Microsoft Edge: {e}"}
        try:
            subprocess.Popen(["cmd", "/c", "start", "", "microsoft-edge:"], shell=True)
            self.active_browser = "edge"
            self.context["active_browser"] = "edge"
            return {"done": False, "message": "Tried to open Microsoft Edge via protocol."}
        except Exception as e:
            return {"done": False, "message": f"Could not open Microsoft Edge: {e}"}

    def _open_store(self):
        try:
            subprocess.Popen(["cmd", "/c", "start", "", "ms-windows-store:"], shell=True)
            return {"done": False, "message": "Opened Microsoft Store."}
        except Exception as e:
            return {"done": False, "message": f"Could not open Microsoft Store: {e}"}

    def _open_brave(self):
        possible_paths = [
            Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
            Path(r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        for path in possible_paths:
            if path.exists():
                try:
                    subprocess.Popen([str(path)])
                    return {"done": False, "message": "Opened Brave."}
                except Exception as e:
                    return {"done": False, "message": f"Failed to open Brave: {e}"}
        try:
            subprocess.Popen(["brave"])
            self.active_browser = "brave"
            self.context["active_browser"] = "brave"
            return {"done": False, "message": "Tried to open Brave from PATH."}
        except Exception as e:
            return {"done": False, "message": f"Brave not found: {e}"}

    def _open_whatsapp(self):
        # Try classic desktop locations
        candidates = [
            self.user_home / "AppData" / "Local" / "WhatsApp" / "WhatsApp.exe",
            self.user_home / "AppData" / "Local" / "Programs" / "WhatsApp" / "WhatsApp.exe",
        ]
        for path in candidates:
            if path.is_file():
                try:
                    subprocess.Popen([str(path)])
                    return {"done": False, "message": "Opened WhatsApp."}
                except Exception as e:
                    return {"done": False, "message": f"Failed to open WhatsApp: {e}"}

        # Try WhatsApp URI (for Store / modern app)
        try:
            subprocess.Popen(["cmd", "/c", "start", "", "whatsapp:"], shell=True)
            return {"done": False, "message": "Tried to open WhatsApp via protocol."}
        except Exception as e:
            return {"done": False, "message": f"Could not open WhatsApp automatically: {e}"}
        
    def _open_comet(self):
        # Try some typical locations, then fall back to generic shell start
        possible_paths = [
            Path(r"C:\Program Files\Comet\Comet.exe"),
            Path(r"C:\Program Files (x86)\Comet\Comet.exe"),
        ]
        for path in possible_paths:
            if path.exists():
                try:
                    subprocess.Popen([str(path)])
                    return {"done": False, "message": "Opened Comet."}
                except Exception as e:
                    return {"done": False, "message": f"Failed to open Comet: {e}"}

        # Fallback: let Windows resolve 'comet' via Start/search
        try:
            subprocess.Popen(["cmd", "/c", "start", "", "comet"], shell=True)
            return {"done": False, "message": "Tried to open Comet using Windows shell."}
        except Exception as e:
            return {"done": False, "message": f"Could not open Comet via Windows shell: {e}"}
        
    def _search_start_menu_shortcut(self, target: str) -> Path | None:
        target = target.lower()

        programdata = os.environ.get("PROGRAMDATA")
        appdata = os.environ.get("APPDATA")

        start_dirs = []
        if programdata:
            start_dirs.append(Path(programdata) / "Microsoft/Windows/Start Menu/Programs")
        if appdata:
            start_dirs.append(Path(appdata) / "Microsoft/Windows/Start Menu/Programs")

        best_match = None
        best_score = 0.0

        for base in start_dirs:
            if not base.exists():
                continue
            for p in base.rglob("*.lnk"):
                name = p.stem.lower()

                score = max(
                    similarity(target, name),
                    similarity(target.replace(" ", ""), name.replace(" ", "")),
                )

                if score > best_score:
                    best_score = score
                    best_match = p

        if best_score > 0.62:
            return best_match

        return None
    
    def execute_search_from_pending(self, query: str):
        """
        Called by the orchestrator when a pending_search exists and the user provides the query.
        Performs the appropriate in-app search (prefers browser in pending_search).
        Clears pending_search afterwards.
        """
        if not self.pending_search:
            return {"done": False, "message": "No pending search found."}

        engine = self.pending_search.get("engine")   # None means infer from context/last_search
        browser = self.pending_search.get("browser") # e.g., 'chrome'
        new_tab = self.pending_search.get("new_tab", False)

        # If the browser hint is given and is chrome, try to focus Chrome specifically
        # (we still use _in_app_search which focuses any browser)
        # perform the in-app search
        result = self._in_app_search(engine, query, new_tab)

        # Clear pending context
        self.pending_search = None
        return result
    
    def _resolve_browser(self, explicit_browser):
        if explicit_browser:
            return explicit_browser
        return self.active_browser
    
    def _detect_active_browser(self):
        try:
            desktop = Desktop(backend="uia")
            aw = desktop.active()
            title = (aw.window_text() or "").lower()

            if "brave" in title:
                return "brave"
            if "chrome" in title:
                return "chrome"
            if "edge" in title:
                return "edge"
        except Exception:
            pass

        return None

    
    def _focus_any_browser(self, prefer: list | None = None) -> bool:
        if not Desktop:
            return False
        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows()
            # prefer list like ['chrome', 'edge']
            if prefer:
                for p in prefer:
                    for w in windows:
                        try:
                            title = (w.window_text() or "").lower()
                        except Exception:
                            continue
                        if p in title:
                            try:
                                w.set_focus()
                                return True
                            except Exception:
                                continue
            # fallback: any browser
            for w in windows:
                try:
                    title = (w.window_text() or "")
                except Exception:
                    continue
                lt = title.lower()
                if any(b in lt for b in ("chrome", "edge", "brave", "firefox","comet", "opera", "vivaldi", "yandex","safari","chromium","msedge","google")):
                    try:
                        w.set_focus()
                        return True
                    except Exception:
                        continue
        except Exception:
            return False
        return False

    
    def _open_nth_from_last_search(self, index: int):
        if not self.last_search_links:
            return {"done": False, "message": "No stored links from last search."}

        if index <= 0:
            index = 1

        if index > len(self.last_search_links):
            return {
                "done": False,
                "message": f"There are only {len(self.last_search_links)} results."
            }

        url = self.last_search_links[index - 1]
        return self._navigate_in_current_tab(url)


    def _play_nth_youtube_video(self, index: int):
        if not self.last_search_url:
            return {
                "done": False,
                "message": "Search YouTube first, then say play the video."
            }

        # YouTube search results page → use &sp index trick
        video_url = f"{self.last_search_url}&sp=EgIQAQ%253D%253D"

        try:
            send_keys("^l")
            send_keys(video_url, with_spaces=False)
            send_keys("{ENTER}")
            return {
                "done": False,
                "message": f"Playing YouTube video #{index}."
            }
        except Exception:
            os.startfile(video_url)
            return {
                "done": False,
                "message": f"Opened YouTube results for video #{index}."
            }
            
    def execute_search_from_pending(self, query):
        engine = self.pending_search.get("engine")
        self.pending_search = None
        return self._in_app_search(engine, query, new_tab=False)


    def _open_nth_youtube(self, index: int):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            resp = requests.get(self.last_search_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return {
                    "done": False,
                    "message": f"Couldn't load YouTube results (status {resp.status_code})."
                }

            text = resp.text

            # YouTube embeds JSON as ytInitialData
            m = re.search(r"ytInitialData\"\s*:\s*({.*?})\s*[,<]", text, re.S)
            if not m:
                # fallback to older pattern
                m = re.search(r"var ytInitialData\s*=\s*({.*?});", text, re.S)

            if not m:
                return {
                    "done": False,
                    "message": "Couldn't locate YouTube initial data on the page."
                }

            data = json.loads(m.group(1))

            video_ids = self._extract_youtube_video_ids(data)
            if not video_ids:
                return {
                    "done": False,
                    "message": "Couldn't find any videos on the YouTube results page."
                }

            if index > len(video_ids):
                return {
                    "done": False,
                    "message": f"There are only {len(video_ids)} videos; can't open item #{index}."
                }

            vid = video_ids[index - 1]
            video_url = f"https://www.youtube.com/watch?v={vid}"
            return self._navigate_in_current_tab(video_url)


        except Exception as e:
            return {
                "done": False,
                "message": f"Failed to open YouTube video #{index}: {e}"
            }


    def _extract_youtube_video_ids(self, data):
        """
        Try to extract video IDs from the *main search results* section,
        not from sidebars or recommendations.
        """
        # First, try the structured path YouTube uses for search results
        try:
            contents = data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]

            # Sometimes primaryContents is directly a 'sectionListRenderer'
            if "sectionListRenderer" in contents:
                sections = contents["sectionListRenderer"]["contents"]
            else:
                sections = contents["richGridRenderer"]["contents"]

            ordered_ids = []

            for section in sections:
                item_section = section.get("itemSectionRenderer")
                if not item_section:
                    # richGridRenderer / other layouts
                    grid = section.get("richGridRenderer")
                    if grid:
                        for item in grid.get("contents", []):
                            rich_item = item.get("richItemRenderer")
                            if not rich_item:
                                continue
                            video = rich_item.get("content", {}).get("videoRenderer")
                            if video and "videoId" in video:
                                ordered_ids.append(video["videoId"])
                    continue

                for item in item_section.get("contents", []):
                    video = item.get("videoRenderer")
                    if video and "videoId" in video:
                        ordered_ids.append(video["videoId"])

            if ordered_ids:
                return ordered_ids

        except Exception:
            # fall back to generic scan if this path fails
            pass

        # Fallback: generic DFS collecting videoId (may include sidebars)
        video_ids = set()

        def walk(o):
            if isinstance(o, dict):
                if "videoId" in o and isinstance(o["videoId"], str):
                    video_ids.add(o["videoId"])
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for item in o:
                    walk(item)

        walk(data)
        return list(video_ids)


    def _open_nth_web(self, index: int):
        if not self.last_links:
            return {
                "done": False,
                "message": "No stored links from last search."
            }

        if index <= 0:
            index = 1

        if index > len(self.last_links):
            return {
                "done": False,
                "message": f"There are only {len(self.last_links)} results."
            }

        target = self.last_links[index - 1]
        webbrowser.open(target)

        return {
            "done": False,
            "message": f"Opened result #{index}."
        }

    def _add_note(self, content: str):
        if not content:
            return {"done": False, "message": "What should I note?"}

        notes_dir = Path.home() / "MAX_NOTES"
        notes_file = notes_dir / "notes.txt"

        try:
            notes_dir.mkdir(exist_ok=True)

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(notes_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {content}\n")

            return {
                "done": False,
                "message": f"Noted: {content}"
            }
        except Exception as e:
            return {
                "done": False,
                "message": f"Failed to save note: {e}"
            }



    def _open_nth_web_duckduckgo(self, query: str, index: int):
            url = f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(res.text, "html.parser")

            links = []
            for a in soup.select("a.result__a"):
                href = a.get("href")
                if href and href.startswith("http"):
                    links.append(href)

            if index <= 0 or index > len(links):
                return {"message": f"No result #{index} found.", "done": False}

            webbrowser.open(links[index - 1])
            return {"message": f"Opened result #{index}.", "done": False}


            
    def _navigate_in_current_tab(self, url: str):
        # update context
        lu = url.lower()
        if "youtube.com" in lu:
            self.last_search_engine = "youtube"
        elif "google.com/search" in lu:
            self.last_search_engine = "google"
        self.last_search_url = url

        # attempt to focus existing browser tab and navigate in-place
        if not self._focus_any_browser():
            # fallback: open normally
            return self._open_url(url)
        try:
            send_keys("^l")  # focus address bar
            send_keys(url, with_spaces=False)
            send_keys("{ENTER}")
            return {"done": False, "message": f"Opened {url} in current tab."}
        except Exception:
            return self._open_url(url)

    
    def _search_file_or_folder_by_name(self, target: str, location=None) -> Path | None:
        name = target.lower()
        roots = []

        special_base = self._get_special_base(location)
        if special_base is not None:
            roots.append(special_base)

        roots.append(self.config.get_root_path())
        roots.append(self.user_home / "Desktop")
        roots.append(self.user_home / "Documents")
        roots.append(self.user_home / "Downloads")

        seen = set()
        candidates = []
        labels = []

        for base in roots:
            if not base or not base.exists():
                continue
            base = base.resolve()
            if base in seen:
                continue
            seen.add(base)
            try:
                for p in base.rglob("*"):
                    if p.is_dir() or p.is_file():
                        stem = p.stem.lower()
                        labels.append(stem)
                        candidates.append(p)
                    if len(candidates) >= 5000:
                        break
            except Exception:
                continue
            if len(candidates) >= 5000:
                break

        if not labels:
            return None

        matches = get_close_matches(name, labels, n=1, cutoff=0.8)
        if not matches:
            return None

        best_label = matches[0]
        for p, label in zip(candidates, labels):
            if label == best_label:
                return p

        return None

    def _semantic_file_search(self, query: str):
        """
        Finds files by date/type hints.
        Examples: "yesterday's ppt", "latest resume", "most recent pdf"
        Returns the best matching Path or None.
        """
        import datetime

        q = query.lower()

        # -- Date hint detection
        now = datetime.datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if "yesterday" in q or "yesterday's" in q:
            date_hint = today_start - datetime.timedelta(days=1)
            date_end = today_start
        elif "today" in q or "today's" in q:
            date_hint = today_start
            date_end = now
        elif "last week" in q or "this week" in q:
            date_hint = today_start - datetime.timedelta(days=7)
            date_end = now
        elif any(w in q for w in ("latest", "recent", "newest", "most recent")):
            date_hint = today_start - datetime.timedelta(days=30)
            date_end = now
        else:
            return None  # No semantic hint

        # -- File type hint detection
        type_map = {
            "ppt": [".ppt", ".pptx"],
            "presentation": [".ppt", ".pptx"],
            "powerpoint": [".ppt", ".pptx"],
            "pdf": [".pdf"],
            "resume": [".pdf", ".docx", ".doc"],
            "cv": [".pdf", ".docx", ".doc"],
            "doc": [".doc", ".docx"],
            "document": [".doc", ".docx", ".odt", ".txt"],
            "word": [".doc", ".docx"],
            "excel": [".xls", ".xlsx", ".csv"],
            "spreadsheet": [".xls", ".xlsx", ".csv"],
            "image": [".jpg", ".jpeg", ".png", ".bmp", ".gif"],
            "photo": [".jpg", ".jpeg", ".png"],
            "video": [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
            "text": [".txt"],
        }

        allowed_exts = None
        for keyword, exts in type_map.items():
            if keyword in q:
                allowed_exts = exts
                break

        # -- Search directories
        search_dirs = [
            self.user_home / "Desktop",
            self.user_home / "Downloads",
            self.user_home / "Documents",
        ]
        onedrive = self.user_home / "OneDrive"
        if onedrive.exists():
            search_dirs += [onedrive / "Desktop", onedrive / "Documents"]

        candidates = []
        date_hint_ts = date_hint.timestamp()
        date_end_ts = date_end.timestamp()

        for base in search_dirs:
            if not base or not base.exists():
                continue
            try:
                for p in base.rglob("*"):
                    if not p.is_file():
                        continue
                    if allowed_exts and p.suffix.lower() not in allowed_exts:
                        continue
                    try:
                        mtime = p.stat().st_mtime
                    except Exception:
                        continue
                    if date_hint_ts <= mtime <= date_end_ts:
                        candidates.append((mtime, p))
            except Exception:
                continue

        if not candidates:
            return None

        # For resume/cv, prefer files whose names contain those keywords
        if "resume" in q or "cv" in q:
            resume_matches = [
                (m, p) for m, p in candidates
                if any(kw in p.stem.lower() for kw in ("resume", "cv", "curriculum"))
            ]
            if resume_matches:
                candidates = resume_matches

        # Most recently modified file wins
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def _get_running_apps(self):

        try:
            result = subprocess.run(
                ["wmic", "process", "get", "name"],
                capture_output=True,
                text=True
            )
            lines = result.stdout.splitlines()
            return [l.strip() for l in lines if l.strip().endswith(".exe")]
        except:
            return []

    def _web_search(self, engine, query, parsed_browser: str | None = None):
        if not query:
            return {"done": False, "message": "Search for what?"}

        # normalize engine
        self.last_search_engine = (engine or "google").lower()
        self.last_search_query = query

        if self.last_search_engine == "youtube":
            url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        else:
            # default to Google
            self.last_search_engine = "google"
            url = f"https://www.google.com/search?q={quote_plus(query)}"

        self.last_search_url = url

        # ✅ Explicit beats context beats default
        # 1) explicit browser from parser (parsed_browser)
        # 2) context: self.context.get("active_browser")
        # 3) default: None (let OS decide)
        browser = None
        if parsed_browser:
            browser = parsed_browser.lower()
        else:
            active = self.context.get("active_browser") if hasattr(self, "context") else None
            if active:
                browser = active.lower()

        if browser == "brave":
            subprocess.Popen([
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                url
            ])
            return {
                "done": False,
                "message": f"Searched {self.last_search_engine} for '{query}' in Brave."
            }

        if browser == "chrome":
            subprocess.Popen([
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                url
            ])
            return {
                "done": False,
                "message": f"Searched {self.last_search_engine} for '{query}' in Chrome."
            }

        if browser == "edge":
            subprocess.Popen([
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                url
            ])
            return {
                "done": False,
                "message": f"Searched {self.last_search_engine} for '{query}' in Edge."
            }

        # default behavior (no explicit/context browser)
        os.startfile(url)
        return {
            "done": False,
            "message": f"Searched {self.last_search_engine} for '{query}'."
        }
        
    
    def _handle_open_and_search(self, target: str, query: str, engine: str | None, browser: str | None, new_tab: bool):
        if not target or not query:
            return {"done": False, "message": "Open and search needs both a target and a query."}

        # Decide engine
        actual_engine = engine or target.lower()

        # Build URL
        if actual_engine == "youtube":
            self.last_search_engine = "youtube"
            self.last_search_query = query
            url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"

        else:
            self.last_search_engine = "google"
            self.last_search_query = query
            url = f"https://www.google.com/search?q={quote_plus(query)}"

        self.last_search_url = url

        # Open in requested browser if specified
        if browser:
            opened = self._open_url_in_browser(browser, url)
            if opened:
                return {
                    "done": False,
                    "message": f"Opened {actual_engine} and searched for '{query}' in {browser}."
                }

        # Fallback: default browser
        os.startfile(url)
        return {
            "done": False,
            "message": f"Opened {actual_engine} and searched for '{query}'."
        }




    def _store_search_results(self, engine: str, query: str):
        self.last_search_links = []

        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            q = quote_plus(query)

            if engine == "youtube":
                url = f"https://www.youtube.com/results?search_query={q}"
                r = requests.get(url, headers=headers, timeout=8)

                # extract video IDs
                ids = re.findall(r"\"videoId\":\"([^\"]+)\"", r.text)
                seen = []
                for vid in ids:
                    if vid not in seen:
                        seen.append(f"https://www.youtube.com/watch?v={vid}")
                self.last_search_links = seen

            else:
                url = f"https://www.google.com/search?q={q}"
                r = requests.get(url, headers=headers, timeout=8)
                soup = BeautifulSoup(r.text, "html.parser")

                for a in soup.select("a[href]"):
                    href = a.get("href")
                    if href and href.startswith("/url?q="):
                        clean = href.split("/url?q=")[1].split("&")[0]
                        if clean.startswith("http"):
                            self.last_search_links.append(clean)

        except Exception:
            self.last_search_links = []

    
    def _scrape_links_google(self, query: str):
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(res.text, "html.parser")
        links = []

        for a in soup.select("a"):
            href = a.get("href", "")
            if href.startswith("/url?q="):
                clean = href.split("/url?q=")[1].split("&")[0]
                if clean.startswith("http"):
                    links.append(clean)

        # remove duplicates + junk
        links = [
            l for l in links
            if "google.com" not in l
            and "accounts.google" not in l
        ]

        return list(dict.fromkeys(links))  # preserve order
    
    def _open_url(self, url: str, browser: str | None = None, label: str | None = None):
        # Default browser is Brave when none specified
        effective_browser = browser or "brave"

        # Generate a friendly name for voice responses
        if not label:
            # Try to extract a friendly name from the URL
            friendly_map = {
                "youtube.com": "YouTube",
                "google.com": "Google",
                "github.com": "GitHub",
                "leetcode.com": "LeetCode",
                "stackoverflow.com": "Stack Overflow",
                "wikipedia.org": "Wikipedia",
                "reddit.com": "Reddit",
                "twitter.com": "Twitter",
                "linkedin.com": "LinkedIn",
                "instagram.com": "Instagram",
                "facebook.com": "Facebook",
            }
            label = None
            for domain, name in friendly_map.items():
                if domain in url.lower():
                    label = name
                    break
            if not label:
                # Use the domain as the label
                import re as _re
                m = _re.search(r"https?://(?:www\.)?([^/]+)", url)
                label = m.group(1) if m else url

        if self._open_url_in_browser(effective_browser, url):
            return {"done": False, "message": f"Opened {label}."}

        # Fallback: if the specified browser isn't installed, use system default
        os.startfile(url)
        return {"done": False, "message": f"Opened {label}."}
    
    def read_notes(self):
        notes_dir = Path.home() / "MAX_NOTES"
        if not notes_dir.exists():
            return {"done": False, "message": "You have no notes yet."}

        notes = sorted(notes_dir.glob("*.txt"))
        if not notes:
            return {"done": False, "message": "You have no notes yet."}

        content = []
        for n in notes:
            content.append(n.read_text(encoding="utf-8"))

        return {"done": False, "message": "\n".join(content)}
    
    def _run_volume_op(self, op_fn):
        """
        Runs a pycaw volume operation in a fresh thread with STA COM initialization.
        This is required because pywinauto initializes COM in MTA mode on the main
        thread, while pycaw needs STA — mixing them raises WinError -2147417850.
        """
        import threading
        result = {"value": None, "error": None}

        def worker():
            try:
                import comtypes
                comtypes.CoInitialize()   # STA mode in this fresh thread — safe
                from pycaw.pycaw import AudioUtilities
                device = AudioUtilities.GetSpeakers()
                vol = device.EndpointVolume
                result["value"] = op_fn(vol)
            except Exception as e:
                result["error"] = e
            finally:
                try:
                    import comtypes
                    comtypes.CoUninitialize()
                except Exception:
                    pass

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(timeout=5)

        if result["error"]:
            raise result["error"]
        return result["value"]

    def _mute_volume(self):
        try:
            self._run_volume_op(lambda vol: vol.SetMute(1, None))
            return {"done": False, "message": "Volume muted."}
        except Exception as e:
            return {"done": False, "message": f"Could not mute volume: {e}"}

    def _unmute_volume(self):
        try:
            self._run_volume_op(lambda vol: vol.SetMute(0, None))
            return {"done": False, "message": "Volume unmuted."}
        except Exception as e:
            return {"done": False, "message": f"Could not unmute volume: {e}"}

    def _volume_up(self, amount: int = 10):
        try:
            step = max(1, min(amount, 100)) / 100.0

            def op(vol):
                current = vol.GetMasterVolumeLevelScalar()
                new_level = min(current + step, 1.0)
                vol.SetMasterVolumeLevelScalar(new_level, None)
                return round(new_level * 100)

            new_pct = self._run_volume_op(op)
            return {"done": False, "message": f"Volume increased to {new_pct}%."}
        except Exception as e:
            return {"done": False, "message": f"Could not increase volume: {e}"}

    def _volume_down(self, amount: int = 10):
        try:
            step = max(1, min(amount, 100)) / 100.0

            def op(vol):
                current = vol.GetMasterVolumeLevelScalar()
                new_level = max(current - step, 0.0)
                vol.SetMasterVolumeLevelScalar(new_level, None)
                return round(new_level * 100)

            new_pct = self._run_volume_op(op)
            return {"done": False, "message": f"Volume decreased to {new_pct}%."}
        except Exception as e:
            return {"done": False, "message": f"Could not decrease volume: {e}"}


    def _set_volume(self, level):
        try:
            level = max(0, min(level, 100))
            self._run_volume_op(lambda vol: vol.SetMasterVolumeLevelScalar(level / 100, None))
            return {"done": False, "message": f"Volume set to {level}%."}
        except Exception as e:
            return {"done": False, "message": f"Could not set volume: {e}"}

    # ─── BRIGHTNESS CONTROL ───────────────────────────────────────────────

    def _get_brightness(self) -> int | None:
        """Gets the current screen brightness (0-100) via PowerShell WMI."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"],
                capture_output=True, text=True, timeout=5
            )
            return int(result.stdout.strip())
        except Exception:
            return None

    def _set_brightness(self, level: int):
        """Sets screen brightness to a specific percentage (0-100)."""
        level = max(0, min(level, 100))
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                 f".WmiSetBrightness(1, {level})"],
                capture_output=True, text=True, timeout=5
            )
            return {"done": False, "message": f"Brightness set to {level}%."}
        except Exception as e:
            return {"done": False, "message": f"Could not set brightness: {e}"}

    def _brightness_up(self, amount: int = 10):
        """Increases screen brightness by `amount` percent."""
        try:
            current = self._get_brightness()
            if current is None:
                return {"done": False, "message": "Could not read current brightness."}
            new_level = min(current + amount, 100)
            return self._set_brightness(new_level)
        except Exception as e:
            return {"done": False, "message": f"Could not increase brightness: {e}"}

    def _brightness_down(self, amount: int = 10):
        """Decreases screen brightness by `amount` percent."""
        try:
            current = self._get_brightness()
            if current is None:
                return {"done": False, "message": "Could not read current brightness."}
            new_level = max(current - amount, 0)
            return self._set_brightness(new_level)
        except Exception as e:
            return {"done": False, "message": f"Could not decrease brightness: {e}"}






    def _in_app_search(self, engine: str | None, query: str, new_tab: bool, browser: str | None = None):
        if browser:
            focused = self._focus_specific_browser(browser)
            if not focused:
                return {"done": False, "message": f"{browser.capitalize()} is not open."}

        if not query:
            return {"done": False, "message": "Search for what?"}

        # 1) If engine not specified, infer from active browser first
        if engine is None:
            if getattr(self, "active_browser", None) == "youtube":
                engine = "youtube"
            else:
                engine = self.last_search_engine or "google"

        engine = engine.lower()

        # 🔥 CRITICAL: STORE SEARCH RESULTS
        self._store_search_results(engine, query)

        self.last_search_engine = engine
        self.last_search_query = query

        # Build URL
        if engine == "youtube":
            url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        else:
            engine = "google"  # normalize any non-youtube to google
            url = f"https://www.google.com/search?q={quote_plus(query)}"

        self.last_search_url = url

        try:
            if new_tab:
                send_keys("^t")
            send_keys("^l")
            send_keys(url, with_spaces=False)
            send_keys("{ENTER}")
            return {
                "done": False,
                "message": (
                    f"Searched {engine} for '{query}' in "
                    f"{'new' if new_tab else 'current'} tab."
                ),
            }
        except Exception:
            return self._web_search(engine, query)
        
    def _focus_specific_browser(self, browser: str) -> bool:
        if not Desktop:
            return False
        try:
            desktop = Desktop(backend="uia")
            for w in desktop.windows():
                title = (w.window_text() or "").lower()
                if browser in title:
                    w.set_focus()
                    return True
        except Exception:
            pass
        return False

    def _open_url_in_browser(self, browser: str, url: str):
        browser_paths = {
            "chrome": [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ],
            "brave": [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            ],
            "edge": [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            ],
        }

        for path in browser_paths.get(browser, []):
            if os.path.exists(path):
                subprocess.Popen([path, url])
                return True
        return False



    def _open_generic_app(self, name: str):
        try:
            subprocess.Popen(["cmd", "/c", "start", "", name], shell=True)
            return {"done": False, "message": f"Tried to open '{name}' using Windows shell."}
        except Exception as e:
            return {"done": False, "message": f"Could not open '{name}' via Windows shell: {e}"}

    def _create_folder(self, name: str, location=None):
        if not name:
            return {"done": False, "message": "Folder name missing."}

        path = self._resolve_path(name, location)

        try:
            path.mkdir(parents=True, exist_ok=False)
            return {"done": False, "message": f"Created folder '{path.name}'."}
        except FileExistsError:
            return {"done": False, "message": f"Folder '{path.name}' already exists."}
        except Exception as e:
            return {"done": False, "message": f"Failed to create folder: {e}"}

    def _create_file(self, name: str, text_default: bool, location=None):
        if not name:
            return {"done": False, "message": "File name missing."}

        if text_default and not name.lower().endswith(".txt"):
            name = name + ".txt"

        path = self._resolve_path(name, location)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                return {"done": False, "message": f"File '{path.name}' already exists."}
            path.touch()
            return {"done": False, "message": f"Created file '{path.name}'."}
        except Exception as e:
            return {"done": False, "message": f"Failed to create file: {e}"}

    def _delete_path(self, target: str, location=None):
        if not target:
            return {"done": False, "message": "Delete what?"}

        path = self._resolve_path(target, location)

        if not path.exists():
            return {"done": False, "message": f"'{target}' not found."}

        try:
            if path.is_dir():
                shutil.rmtree(path)
                return {"done": False, "message": f"Deleted folder '{path.name}'."}
            else:
                path.unlink()
                return {"done": False, "message": f"Deleted file '{path.name}'."}
        except Exception as e:
            return {"done": False, "message": f"Failed to delete: {e}"}

    def _close_chrome(self):
        try:
            subprocess.run(["taskkill", "/IM", "chrome.exe", "/F"], capture_output=True)
            return {"done": False, "message": "Closed Chrome."}
        except Exception as e:
            return {"done": False, "message": f"Failed to close Chrome: {e}"}

    def _close_notepad(self):
        try:
            subprocess.run(["taskkill", "/IM", "notepad.exe", "/F"], capture_output=True)
            return {"done": False, "message": "Closed Notepad."}
        except Exception as e:
            return {"done": False, "message": f"Failed to close Notepad: {e}"}

    def _close_windows_by_title(self, keyword: str):
        if not Desktop:
            return {"done": False, "message": "Window control not available (pywinauto not installed)."}

        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows()
            closed_any = False
            kw = keyword.lower()
            for w in windows:
                try:
                    title = (w.window_text() or "").lower()
                except Exception:
                    continue
                if kw and kw in title:
                    try:
                        w.close()
                        closed_any = True
                    except Exception:
                        pass

            if closed_any:
                return {"done": False, "message": f"Closed windows matching '{keyword}'."}
            return {"done": False, "message": f"No open windows matching '{keyword}' found."}
        except Exception as e:
            return {"done": False, "message": f"Couldn't inspect windows to close '{keyword}': {e}"}
        
        
