"""
EventMonitor — Background event detection for MAX (FR-11, FR-12)
Monitors system events (download complete, file copy done, video end)
and fires a queued action when the event occurs.
"""

import threading
import time
import os
import subprocess
from pathlib import Path


class EventMonitor:
    def __init__(self, scheduler):
        """
        :param scheduler: AutomationScheduler instance to fire actions on event.
        """
        self._scheduler = scheduler
        self._monitors: list[threading.Thread] = []

    # ─────────────────────────────────────────────────────────────────────────
    # Public API — register an event-action pair
    # ─────────────────────────────────────────────────────────────────────────
    def watch(self, trigger: str, action: str) -> str:
        """
        Register an event watcher.
        trigger: VIDEO_END | DOWNLOAD_DONE | COPY_DONE
        action:  SHUTDOWN | RESTART | LOCK | SLEEP | NOTIFY
        Returns a human-readable confirmation message.
        """
        trigger = trigger.upper()
        action = action.upper()

        if trigger == "DOWNLOAD_DONE":
            msg = self._start_download_watcher(action)
        elif trigger == "VIDEO_END":
            msg = self._start_video_watcher(action)
        elif trigger == "COPY_DONE":
            msg = self._start_copy_watcher(action)
        else:
            msg = f"Unknown trigger: {trigger}"

        return msg

    # ─────────────────────────────────────────────────────────────────────────
    # Download monitor — watches Downloads folder for file stabilization
    # ─────────────────────────────────────────────────────────────────────────
    def _start_download_watcher(self, action: str) -> str:
        downloads = Path.home() / "Downloads"
        thread = threading.Thread(
            target=self._watch_download,
            args=(downloads, action),
            daemon=True,
        )
        thread.start()
        self._monitors.append(thread)
        return f"Watching Downloads folder. Will {action.lower()} when download completes."

    def _watch_download(self, folder: Path, action: str):
        """
        Polls Downloads folder every 3 seconds.
        When a .crdownload / .part / .tmp file disappears → download done.
        """
        PARTIAL_EXTS = {".crdownload", ".part", ".tmp", ".download"}
        poll_interval = 3
        active_partials: set = set()

        print("MAX [EventMonitor] Download watcher started.")

        while True:
            try:
                current_partials = {
                    p.name for p in folder.iterdir()
                    if p.suffix.lower() in PARTIAL_EXTS
                }
                # If we had partials before and now they're gone → done
                if active_partials and not active_partials.intersection(current_partials):
                    print(f"\nMAX> ✅ Download complete! Executing: {action}")
                    self._scheduler.schedule_action(0, action, "Download complete.")
                    return

                active_partials = current_partials or active_partials
            except Exception:
                pass

            time.sleep(poll_interval)

    # ─────────────────────────────────────────────────────────────────────────
    # Video/media end monitor — watches media player CPU usage
    # ─────────────────────────────────────────────────────────────────────────
    def _start_video_watcher(self, action: str) -> str:
        thread = threading.Thread(
            target=self._watch_video,
            args=(action,),
            daemon=True,
        )
        thread.start()
        self._monitors.append(thread)
        return f"Watching media players. Will {action.lower()} when video ends."

    def _watch_video(self, action: str):
        """
        Monitors known media player processes via psutil.
        When CPU usage drops to ~0 for 10+ seconds → video likely ended.
        """
        try:
            import psutil
        except ImportError:
            print("MAX [EventMonitor] psutil not installed. Run: pip install psutil")
            return

        MEDIA_PROCESSES = {
            "vlc.exe", "wmplayer.exe", "mpc-hc.exe", "mpc-hc64.exe",
            "mpv.exe", "potplayer.exe", "potplayermini.exe",
            "movies & tv", "video.ui.exe",
        }

        poll_interval = 5
        low_cpu_count = 0
        REQUIRED_LOW_CPU_CYCLES = 3  # 3×5s = 15s of low CPU = ended

        print("MAX [EventMonitor] Video watcher started.")

        while True:
            found_active = False
            for proc in psutil.process_iter(["name", "cpu_percent"]):
                try:
                    pname = (proc.info["name"] or "").lower()
                    if pname in MEDIA_PROCESSES:
                        cpu = proc.cpu_percent(interval=1)
                        if cpu > 1.0:
                            found_active = True
                            low_cpu_count = 0
                            break
                except Exception:
                    continue

            if not found_active:
                low_cpu_count += 1
            else:
                low_cpu_count = 0

            if low_cpu_count >= REQUIRED_LOW_CPU_CYCLES:
                print(f"\nMAX> ✅ Video appears to have ended! Executing: {action}")
                self._scheduler.schedule_action(0, action, "Video ended.")
                return

            time.sleep(poll_interval)

    # ─────────────────────────────────────────────────────────────────────────
    # Copy/transfer monitor — watches clipboard / file system for copy ops
    # ─────────────────────────────────────────────────────────────────────────
    def _start_copy_watcher(self, action: str) -> str:
        thread = threading.Thread(
            target=self._watch_copy,
            args=(action,),
            daemon=True,
        )
        thread.start()
        self._monitors.append(thread)
        return f"Watching for file copy completion. Will {action.lower()} when copying finishes."

    def _watch_copy(self, action: str):
        """
        Detects copy completion by monitoring robocopy-style or shell copy progress.
        Simplified approach: watches for 'explorer.exe' CPU dropping after a brief spike,
        or shell process completion.
        Falls back to a 30-second wait if we can't detect precisely.
        """
        try:
            import psutil
        except ImportError:
            print("MAX [EventMonitor] psutil not installed. Run: pip install psutil")
            time.sleep(30)
            self._scheduler.schedule_action(0, action, "Copy done (estimated).")
            return

        print("MAX [EventMonitor] Copy watcher started. Looking for explorer copy activity...")

        # Wait for explorer to spike CPU (indicating a copy started)
        saw_spike = False
        poll_interval = 2
        idle_count = 0

        while True:
            try:
                for proc in psutil.process_iter(["name", "cpu_percent"]):
                    pname = (proc.info.get("name") or "").lower()
                    if pname == "explorer.exe":
                        cpu = proc.cpu_percent(interval=0.5)
                        if cpu > 10:
                            saw_spike = True
                            idle_count = 0
                        elif saw_spike:
                            idle_count += 1
            except Exception:
                pass

            if saw_spike and idle_count >= 3:
                print(f"\nMAX> ✅ Copy appears complete! Executing: {action}")
                self._scheduler.schedule_action(0, action, "Copy complete.")
                return

            time.sleep(poll_interval)
