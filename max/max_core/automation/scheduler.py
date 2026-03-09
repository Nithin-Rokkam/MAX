import threading
import time
import subprocess
import ctypes


class AutomationScheduler:
    def __init__(self):
        self._tasks = []

    # ── Legacy: notification-only (kept for backward compat) ──────────────────
    def schedule_notification(self, delay_seconds: int, message: str):
        self.schedule_action(delay_seconds, "NOTIFY", message)

    # ── New: action-aware scheduler ───────────────────────────────────────────
    def schedule_action(self, delay_seconds: int, action_type: str, message: str = ""):
        """
        Schedule an OS action after a delay.
        action_type: NOTIFY | SHUTDOWN | LOCK | RESTART
        """
        if delay_seconds <= 0:
            print("MAX> Timer delay must be positive.")
            return

        thread = threading.Thread(
            target=self._action_thread,
            args=(delay_seconds, action_type, message),
            daemon=True,
        )
        thread.start()
        self._tasks.append(thread)

    def _action_thread(self, delay_seconds: int, action_type: str, message: str):
        time.sleep(delay_seconds)

        action_type = action_type.upper()

        if action_type == "NOTIFY":
            print(f"\nMAX> ⏰ Reminder: {message}")
            print("you> ", end="", flush=True)

        elif action_type == "SHUTDOWN":
            print("\nMAX> ⏻ Shutting down the system now...")
            print("you> ", end="", flush=True)
            time.sleep(1)
            subprocess.run(["shutdown", "/s", "/t", "0"], shell=True)

        elif action_type == "RESTART":
            print("\nMAX> 🔄 Restarting the system now...")
            print("you> ", end="", flush=True)
            time.sleep(1)
            subprocess.run(["shutdown", "/r", "/t", "0"], shell=True)

        elif action_type == "LOCK":
            print("\nMAX> 🔒 Locking the screen now...")
            print("you> ", end="", flush=True)
            ctypes.windll.user32.LockWorkStation()

        elif action_type == "SLEEP":
            print("\nMAX> 💤 Putting system to sleep...")
            print("you> ", end="", flush=True)
            subprocess.run(
                ["powercfg", "-hibernate", "off"],
                capture_output=True, shell=True
            )
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])

        else:
            print(f"\nMAX> Unknown scheduled action: {action_type}")
            print("you> ", end="", flush=True)
