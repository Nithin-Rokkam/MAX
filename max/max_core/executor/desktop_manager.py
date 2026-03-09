"""
DesktopManager — Cross-Desktop Intelligent Interaction (CDII) for MAX
Implements FR-09 and FR-10: identify apps on each desktop and interact
without switching the visible desktop.

Requires: pip install pyvda pywinauto
"""

import time
import subprocess
from pywinauto.keyboard import send_keys

try:
    import pyvda
    PYVDA_AVAILABLE = True
except ImportError:
    PYVDA_AVAILABLE = False

try:
    from pywinauto import Desktop as PywinDesktop
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False


# Map of spoken app names to process/window title fragments
APP_TITLE_MAP = {
    "youtube":    ["youtube", "yt"],
    "chrome":     ["chrome", "google chrome"],
    "edge":       ["edge", "microsoft edge"],
    "brave":      ["brave"],
    "firefox":    ["firefox", "mozilla"],
    "notepad":    ["notepad"],
    "explorer":   ["file explorer", "windows explorer", "this pc"],
    "vlc":        ["vlc media player", "vlc"],
    "spotify":    ["spotify"],
    "word":       ["word", "microsoft word"],
    "excel":      ["excel", "microsoft excel"],
    "vscode":     ["visual studio code", "vscode", "code"],
}

# Map of media actions to keyboard shortcuts
MEDIA_KEYS = {
    "pause":  "{VK_MEDIA_PLAY_PAUSE}",
    "play":   "{VK_MEDIA_PLAY_PAUSE}",
    "stop":   "{VK_MEDIA_STOP}",
    "next":   "{VK_MEDIA_NEXT_TRACK}",
    "prev":   "{VK_MEDIA_PREV_TRACK}",
    "previous": "{VK_MEDIA_PREV_TRACK}",
    "mute":   "{VK_VOLUME_MUTE}",
    "unmute": "{VK_VOLUME_MUTE}",
}


class DesktopManager:
    def __init__(self):
        pass

    def is_available(self) -> bool:
        return PYVDA_AVAILABLE and PYWINAUTO_AVAILABLE

    # ─────────────────────────────────────────────────────────────────────────
    # FR-09: List windows on a specific virtual desktop
    # ─────────────────────────────────────────────────────────────────────────
    def get_apps_on_desktop(self, desktop_num: int) -> list[str]:
        """
        Returns a list of window titles running on virtual desktop #desktop_num.
        Desktop numbering starts at 1.
        """
        if not PYVDA_AVAILABLE:
            return self._fallback_running_windows()

        try:
            desktops = pyvda.get_virtual_desktops()
            idx = desktop_num - 1  # 0-indexed

            if idx < 0 or idx >= len(desktops):
                return []

            target_desktop = desktops[idx]
            apps_on_desktop = pyvda.get_apps_by_z_order(switcher_windows=False, current_desktop=False)

            titles = []
            for app in apps_on_desktop:
                try:
                    if app.desktop_id == target_desktop.id:
                        title = app.window_title or ""
                        if title.strip():
                            titles.append(title.strip())
                except Exception:
                    continue

            return titles

        except Exception as e:
            print(f"MAX [CDII] pyvda error: {e}")
            return self._fallback_running_windows()

    def get_all_desktops_summary(self) -> dict[int, list[str]]:
        """Returns {desktop_num: [window_titles]} for all desktops."""
        if not PYVDA_AVAILABLE:
            return {1: self._fallback_running_windows()}

        try:
            desktops = pyvda.get_virtual_desktops()
            result = {}
            apps = pyvda.get_apps_by_z_order(switcher_windows=False, current_desktop=False)

            for i, desk in enumerate(desktops, start=1):
                titles = []
                for app in apps:
                    try:
                        if app.desktop_id == desk.id:
                            title = app.window_title or ""
                            if title.strip():
                                titles.append(title.strip())
                    except Exception:
                        continue
                result[i] = titles

            return result
        except Exception:
            return {1: self._fallback_running_windows()}

    # ─────────────────────────────────────────────────────────────────────────
    # FR-10: Interact with an app on another desktop WITHOUT switching
    # ─────────────────────────────────────────────────────────────────────────
    def control_app_on_desktop(self, app_name: str, desktop_num: int, action: str) -> str:
        """
        Sends a keyboard action to an app on a specific desktop without switching.
        Returns a status message.
        """
        if not (PYVDA_AVAILABLE and PYWINAUTO_AVAILABLE):
            return self._fallback_control(app_name, action)

        try:
            # Find the target window handle
            hwnd = self._find_window_on_desktop(app_name, desktop_num)
            if hwnd is None:
                return f"Could not find '{app_name}' on Desktop {desktop_num}."

            # Move it to current desktop temporarily, act, then move back
            current_desktop = pyvda.get_current_desktop()
            target_virtual_desktop_idx = desktop_num - 1
            desktops = pyvda.get_virtual_desktops()

            if target_virtual_desktop_idx >= len(desktops):
                return f"Desktop {desktop_num} does not exist."

            target_desktop = desktops[target_virtual_desktop_idx]

            # Bring the window to current desktop, do action, send back
            app = pyvda.AppView(hwnd=hwnd)
            app.move(current_desktop)
            time.sleep(0.3)

            result = self._send_action_to_hwnd(hwnd, action)

            time.sleep(0.2)
            app.move(target_desktop)
            return result

        except Exception as e:
            return f"CDII error: {e}"

    def _find_window_on_desktop(self, app_name: str, desktop_num: int):
        """Finds the HWND of a window matching app_name on desktop_num."""
        titles_on_desktop = self.get_apps_on_desktop(desktop_num)
        app_lower = app_name.lower()

        # Get keywords for this app
        keywords = APP_TITLE_MAP.get(app_lower, [app_lower])

        for title in titles_on_desktop:
            title_lower = title.lower()
            if any(kw in title_lower for kw in keywords):
                # Now get the HWND from pywinauto
                try:
                    desktop = PywinDesktop(backend="uia")
                    for w in desktop.windows():
                        try:
                            if w.window_text().strip() == title:
                                return w.handle
                        except Exception:
                            continue
                except Exception:
                    pass

        return None

    def _send_action_to_hwnd(self, hwnd, action: str) -> str:
        """Send keyboard/media action to a window by handle."""
        action_lower = action.lower()

        # Media keys via pywinauto
        if action_lower in MEDIA_KEYS:
            key = MEDIA_KEYS[action_lower]
            try:
                import win32gui
                import win32con
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.2)
                send_keys(key)
                return f"Sent '{action}' to window."
            except ImportError:
                send_keys(key)
                return f"Sent '{action}' via global media key."

        # Close
        if action_lower in ("close", "quit", "exit"):
            try:
                desktop = PywinDesktop(backend="uia")
                for w in desktop.windows():
                    try:
                        if w.handle == hwnd:
                            w.close()
                            return "Closed the window."
                    except Exception:
                        pass
            except Exception as e:
                return f"Failed to close: {e}"

        return f"Unknown action: {action}"

    def _fallback_running_windows(self) -> list[str]:
        """Returns all visible window titles (no desktop filtering)."""
        if not PYWINAUTO_AVAILABLE:
            return []
        try:
            desktop = PywinDesktop(backend="uia")
            titles = []
            for w in desktop.windows():
                try:
                    t = w.window_text()
                    if t and t.strip():
                        titles.append(t.strip())
                except Exception:
                    continue
            return titles
        except Exception:
            return []

    def _fallback_control(self, app_name: str, action: str) -> str:
        """pyvda not available — try to focus & act on any matching window."""
        if not PYWINAUTO_AVAILABLE:
            return "CDII not available: pyvda and pywinauto required."

        app_lower = app_name.lower()
        keywords = APP_TITLE_MAP.get(app_lower, [app_lower])

        try:
            desktop = PywinDesktop(backend="uia")
            for w in desktop.windows():
                try:
                    title = (w.window_text() or "").lower()
                    if any(kw in title for kw in keywords):
                        w.set_focus()
                        time.sleep(0.3)
                        action_lower = action.lower()
                        if action_lower in MEDIA_KEYS:
                            send_keys(MEDIA_KEYS[action_lower])
                            return f"Sent '{action}' to '{w.window_text()}'."
                        elif action_lower in ("close", "quit"):
                            w.close()
                            return f"Closed '{w.window_text()}'."
                except Exception:
                    continue
        except Exception as e:
            return f"Fallback CDII error: {e}"

        return f"No window matching '{app_name}' found."
