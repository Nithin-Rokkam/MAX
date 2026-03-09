from max_core.interpreter.command_parser import CommandParser
from max_core.executor.command_executor import CommandExecutor
from max_core.executor.desktop_manager import DesktopManager
from max_core.modes.mode_manager import ModeManager
from max_core.security.passphrase_manager import PassphraseManager
from max_core.security.voice_profile_manager import VoiceProfileManager
from max_core.automation.scheduler import AutomationScheduler
from max_core.automation.event_monitor import EventMonitor
from max_core.automation.task_chain import TaskChain
from max_core.config.config_manager import ConfigManager
from max_core.interpreter.nlp_normalizer import normalize_command
from max_core.output.voice_speaker import VoiceSpeaker


class Orchestrator:
    def __init__(self):
        self.parser = CommandParser()
        self.config = ConfigManager()
        self.speaker = VoiceSpeaker()
        self.executor = CommandExecutor(self.config)
        self.mode_manager = ModeManager()
        self.pass_manager = PassphraseManager()
        self.voice_profile = VoiceProfileManager()
        self.scheduler = AutomationScheduler()
        self.desktop_mgr = DesktopManager()
        self.event_monitor = EventMonitor(self.scheduler)
        self.last_search_query = None
        self.last_search_engine = None
        self.pending_confirm = None   # Holds ParsedCommand awaiting YES/NO confirmation
        self.pending_create = None    # Holds ParsedCommand awaiting location for CREATE_FILE/CREATE_FOLDER

    def run_cli_loop(self):
        print("MAX: Text Session Started. Type commands. Type 'exit' to quit.")
        print(f"MAX: Current mode = {self.mode_manager.current_mode()}")
        print(f"MAX: Current root = {self.config.get_root_path()}")

        while True:
            try:
                raw = input("you> ")
            except (EOFError, KeyboardInterrupt):
                print("\nMAX: Goodbye.")
                break

            should_exit = self.handle_raw_command(raw)
            if should_exit:
                break

    def handle_raw_command(self, raw: str) -> bool:
        raw_stripped = (raw or "").strip()

        if not raw_stripped:
            return False

        # ── Pending confirmation gate (for destructive actions) ──────────────
        if self.pending_confirm is not None:
            lc = raw_stripped.lower()
            if lc in ("yes", "y", "confirm", "yeah", "yep", "ok", "okay"):
                confirmed = self.pending_confirm
                self.pending_confirm = None
                # Now actually execute the confirmed action
                intent = confirmed.intent

                # Handle DELETE_FILE confirmation
                if intent == "DELETE_FILE":
                    result = self.executor.execute(confirmed)
                    msg = result.get("message")
                    if msg:
                        print(f"MAX> {msg}")
                        self.speaker.speak(msg)
                    return False

                # Handle system actions (SCHEDULE_ACTION confirmation)
                action = confirmed.entities.get("action", "").upper()
                if action == "SHUTDOWN":
                    import subprocess
                    print("MAX> Shutting down...")
                    self.speaker.speak("Shutting down.")
                    subprocess.run(["shutdown", "/s", "/t", "0"], shell=True)
                elif action == "RESTART":
                    import subprocess
                    print("MAX> Restarting...")
                    self.speaker.speak("Restarting.")
                    subprocess.run(["shutdown", "/r", "/t", "0"], shell=True)
                elif action == "LOCK":
                    self._handle_lock_screen()
                elif action == "SLEEP":
                    import subprocess
                    subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
                return action in ("SHUTDOWN", "RESTART")
            else:
                self.pending_confirm = None
                print("MAX> Action cancelled.")
                self.speaker.speak("Action cancelled.")
                return False

        # ── Pending create: waiting for location ──────────────────────────────
        if self.pending_create is not None:
            lc = raw_stripped.lower()

            if lc in ("cancel", "stop", "never mind", "no"):
                self.pending_create = None
                msg = "Create action cancelled."
                print(f"MAX> {msg}")
                self.speaker.speak(msg)
                return False

            # Map user reply to a location
            loc_map = {
                "desktop": "DESKTOP",
                "downloads": "DOWNLOADS", "download": "DOWNLOADS",
                "documents": "DOCUMENTS", "document": "DOCUMENTS", "docs": "DOCUMENTS",
                "here": None, "current": None, "root": None,
            }

            resolved_loc = None
            matched = False
            for key, val in loc_map.items():
                if key in lc:
                    resolved_loc = val
                    matched = True
                    break

            if not matched:
                # User typed something unexpected — treat it as a subfolder path
                resolved_loc = None

            # Apply location and execute
            pending = self.pending_create
            self.pending_create = None
            pending.entities["location"] = resolved_loc
            result = self.executor.execute(pending)
            msg = result.get("message")
            if msg:
                print(f"MAX> {msg}")
                self.speaker.speak(msg)
            return False

        # If there's a pending conversational search, treat this input as the query
        pending = getattr(self.executor, "pending_search", None)

        if pending:
            lc = raw_stripped.lower()
            
            # allow these words to cancel the pending search
            if lc in ("cancel", "stop", "never mind", "no", "exit", "cancel search"):
                self.executor.pending_search = None
                print()
                print("MAX> Pending search cancelled.")
                return False

            # treat the raw text as the query for the pending search
            normalized = normalize_command(raw_stripped)
            # remove command words
            for prefix in (
                "open chrome and search for",
                "open chrome search for",
                "search for",
                "search",
            ):
                if normalized.startswith(prefix):
                    normalized = normalized[len(prefix):].strip()

            query = normalized

            print()
            print("========== MAX PENDING SEARCH ==========")
            print("RAW        >", raw)
            print("PENDING    >", pending)
            print("TREATED AS >", f"search query = {query}")
            print("=======================================")
            print()
            # Delegate to executor's helper to run pending search and clear it
            
            


            
            try:
                search_res = self.executor.execute_search_from_pending(query)
            except AttributeError:
                # If the executor hasn't implemented execute_search_from_pending, fallback:
                search_res = self.executor.execute(
                    self.parser.parse(f"search for {query}")
                )
                # Clear pending_search defensively
                self.executor.pending_search = None

            if search_res:
                msg = search_res.get("message")
                if msg:
                    print(f"MAX> {msg}")
                    self.speaker.speak(msg)
                return bool(search_res.get("done"))

            return False

        # Normal parsing + execution flow
        parsed = self.parser.parse(raw)
        normalized = normalize_command(raw)

        # **NEW: Handle in-app search queries BEFORE executing** (sets context for executor)
        if parsed.intent == "IN_APP_SEARCH":
            query = parsed.entities.get("query")
            if query:
                self.last_search_query = query
                self.last_search_engine = "duckduckgo"

        print()
        print("========== MAX NLP ==========")
        print("RAW        >", raw)
        print("NORMALIZED >", normalized)
        print("INTENT     >", parsed.intent)
        print("ENTITIES   >", parsed.entities)
        print("================================")
        print()

        # Core single-action handlers
        if parsed.intent == "SET_PASSPHRASE":
            self._handle_set_passphrase(parsed)
            return False

        if parsed.intent == "AUTH_PRIME":
            self._handle_auth_prime(parsed)
            return False

        if parsed.intent == "EXIT_PRIME":
            self._handle_exit_prime()
            return False

        if parsed.intent == "SET_ROOT":
            self._handle_set_root(parsed)
            return False

        if parsed.intent == "SET_TIMER":
            self._handle_set_timer(parsed)
            return False

        if parsed.intent == "SCHEDULE_ACTION":
            self._handle_schedule_action(parsed)
            return False

        if parsed.intent == "LOCK_SCREEN":
            self._handle_lock_screen()
            return False

        if parsed.intent == "UNLOCK_SCREEN":
            self._handle_unlock_screen()
            return False

        if parsed.intent == "ADD_NOTE":
            result = self.executor.execute(parsed)
            msg = result.get("message")
            if msg:
                print(f"MAX> {msg}")
                self.speaker.speak(msg)
            return False
            
        if parsed.intent == "READ_NOTES":
            result = self.executor.read_notes()
            msg = result.get("message")
            if msg:
                print(f"MAX> {msg}")
                self.speaker.speak(msg)
            return False

        if parsed.intent == "ENROLL_VOICE":
            self._handle_enroll_voice()
            return False

        if parsed.intent == "VOICE_STATUS":
            self._handle_voice_status()
            return False

        if parsed.intent == "CDII_CONTROL":
            self._handle_cdii_control(parsed)
            return False

        if parsed.intent == "CDII_LIST":
            self._handle_cdii_list(parsed)
            return False

        if parsed.intent == "EVENT_ACTION":
            self._handle_event_action(parsed)
            return False

        if parsed.intent == "TASK_CHAIN":
            self._handle_task_chain(parsed)
            return False

        # ── Ask for location if CREATE without path ────────────────────────────
        if parsed.intent in ("CREATE_FILE", "CREATE_FOLDER") and not parsed.entities.get("location"):
            self.pending_create = parsed
            name = parsed.entities.get("name", "item")
            kind = "folder" if parsed.intent == "CREATE_FOLDER" else "file"
            msg = f"Where should I create the {kind} '{name}'? (desktop, downloads, documents, or here for current root)"
            print(f"MAX> {msg}")
            self.speaker.speak(f"Where should I create the {kind} {name}?")
            return False

        # ── Fix 9: Confirmation gate for destructive actions ────────────────
        if parsed.intent == "DELETE_FILE" and self.pending_confirm is None:
            target = parsed.entities.get("path", "?")
            self.pending_confirm = parsed
            msg = f"Are you sure you want to delete '{target}'? Say YES to confirm or NO to cancel."
            print(f"MAX> {msg}")
            self.speaker.speak(f"Are you sure you want to delete {target}?")
            return False

        # Permission check based on current mode
        if not self.mode_manager.can_execute(parsed.intent):
            msg = "Permission denied. PRIME mode required for this action."
            print(f"MAX> {msg}")
            self.speaker.speak(msg)
            return False


        parsed.entities["last_search_query"] = self.last_search_query
        parsed.entities["last_search_engine"] = self.last_search_engine
        
        if self.executor.pending_search and parsed.intent == "SEARCH_QUERY":
            result = self.executor.execute_search_from_pending(
                parsed.entities.get("query", "")
            )
            msg = result.get('message')
            if msg:
                print(f"MAX> {msg}")
                self.speaker.speak(msg)
            return False


        # Execute parsed command (now has correct search context)
        result = self.executor.execute(parsed)

        msg = result.get("message")
        if msg:
            print(f"MAX> {msg}")
            self.speaker.speak(msg)

        return bool(result.get("done"))


    def _handle_set_passphrase(self, parsed):
        phrase = parsed.entities.get("phrase", "")
        if len(phrase) < 8:
            print("MAX> Passphrase must be at least 8 characters.")
            self.speaker.speak("Passphrase must be at least 8 characters.")
            return
        self.pass_manager.set_passphrase(phrase)
        print("MAX> Passphrase saved successfully. Use 'enter prime <phrase>' to activate Prime mode.")
        self.speaker.speak("Passphrase saved successfully.")

    def _handle_auth_prime(self, parsed):
        phrase = parsed.entities.get("phrase", "").strip()

        # Check if a passphrase has ever been set
        if not self.pass_manager.has_passphrase():
            print("MAX> No passphrase set. Use 'set passphrase <phrase>' to create one first.")
            return

        # Require passphrase to be provided in the command
        if not phrase:
            print("MAX> Passphrase required. Say: 'enter prime <your passphrase>'")
            return

        # Verify the passphrase against stored hash
        if not self.pass_manager.verify(phrase):
            print("MAX> Incorrect passphrase. PRIME mode NOT activated.")
            self.speaker.speak("Incorrect passphrase.")
            return

        self.mode_manager.activate_prime()
        print("MAX> PRIME mode activated. Welcome.")
        self.speaker.speak("Prime mode activated.")
        print(f"MAX: Current mode = {self.mode_manager.current_mode()}")

    def _handle_exit_prime(self):
        self.mode_manager.deactivate_prime()
        msg = "Switched back to USER mode."
        print(f"MAX> {msg}")
        self.speaker.speak(msg)
        print(f"MAX: Current mode = {self.mode_manager.current_mode()}")

    def _handle_set_root(self, parsed):
        path_str = parsed.entities.get("path", "")
        if not path_str:
            msg = "Root path missing."
            print(f"MAX> {msg}")
            self.speaker.speak(msg)
            return
        path = self.config.set_root_path(path_str)
        msg = f"Root path set to '{path}'."
        print(f"MAX> {msg}")
        self.speaker.speak(msg)

    def _handle_set_timer(self, parsed):
        delay = parsed.entities.get("delay_seconds", 0)
        if delay <= 0:
            msg = "I couldn't understand the delay. Example: 'notify me after 10 seconds'"
            print(f"MAX> {msg}")
            self.speaker.speak(msg)
            return
        self.scheduler.schedule_notification(delay, f"Your {delay} second timer is done.")
        msg = f"Okay, I will notify you after {delay} seconds."
        print(f"MAX> {msg}")
        self.speaker.speak(msg)


    def _handle_schedule_action(self, parsed):
        action = parsed.entities.get("action", "").upper()
        delay = parsed.entities.get("delay_seconds", 0)

        action_labels = {
            "SHUTDOWN": "shut down",
            "RESTART": "restart",
            "LOCK": "lock the screen",
            "SLEEP": "go to sleep",
        }
        label = action_labels.get(action, action.lower())

        if delay <= 0:
            # Immediate action — set pending confirmation
            self.pending_confirm = parsed
            msg = f"Are you sure you want to {label} now? Say YES to confirm or NO to cancel."
            print(f"MAX> {msg}")
            self.speaker.speak(msg)
        else:
            mins = delay // 60
            secs = delay % 60
            if mins > 0:
                time_str = f"{mins} minute(s)"
            else:
                time_str = f"{secs} second(s)"
            self.scheduler.schedule_action(delay, action, f"Executing {label} now.")
            msg = f"Got it. I will {label} in {time_str}."
            print(f"MAX> {msg}")
            self.speaker.speak(msg)

    def _handle_lock_screen(self):
        import ctypes
        print("MAX> Locking the screen...")
        self.speaker.speak("Locking the screen.")
        ctypes.windll.user32.LockWorkStation()

    def _handle_unlock_screen(self):
        # Windows lock screen cannot be bypassed programmatically without admin PIN/password
        print("MAX> To unlock the screen, please enter your Windows PIN or password on the lock screen.")
        self.speaker.speak("Please enter your Windows PIN or password to unlock the screen.")

    def _handle_enroll_voice(self):
        """Records a voice sample and saves the speaker profile."""
        if not self.voice_profile.is_available():
            print("MAX> Voice verification library (resemblyzer) is not installed.")
            print("MAX> Run: pip install resemblyzer soundfile")
            self.speaker.speak("Voice verification library is not installed.")
            return

        import speech_recognition as sr
        from pathlib import Path

        recognizer = sr.Recognizer()
        mic = sr.Microphone()

        print("MAX> Voice enrollment started. I will record 3 samples.")
        self.speaker.speak("Voice enrollment started. Please speak after each beep.")

        samples = []
        for i in range(1, 4):
            print(f"MAX> Sample {i}/3 — Say something for 5 seconds...")
            with mic as source:
                recognizer.adjust_for_ambient_noise(source)
                try:
                    audio = recognizer.listen(source, timeout=8, phrase_time_limit=5)
                    samples.append(audio.get_wav_data())
                    print(f"MAX> Sample {i} captured.")
                except sr.WaitTimeoutError:
                    print(f"MAX> Sample {i}: No speech detected, skipping.")

        if not samples:
            print("MAX> Enrollment failed — no samples captured.")
            self.speaker.speak("Enrollment failed. No voice samples captured.")
            return

        # Use the first successful sample for enrollment
        import io
        wav_bytes = samples[0]
        tmp_path = Path("data/enroll_tmp.wav")
        tmp_path.parent.mkdir(exist_ok=True)
        tmp_path.write_bytes(wav_bytes)

        success = self.voice_profile.enroll(str(tmp_path))
        tmp_path.unlink(missing_ok=True)

        if success:
            print("MAX> ✅ Voice profile saved! Speaker verification is now ACTIVE.")
            self.speaker.speak("Voice profile saved. Speaker verification is now active.")
        else:
            print("MAX> Enrollment failed.")
            self.speaker.speak("Voice enrollment failed. Please try again.")

    def _handle_voice_status(self):
        """Reports current voice verification status."""
        if not self.voice_profile.is_available():
            status = "Voice verification library (resemblyzer) not installed. Run: pip install resemblyzer"
        elif self.voice_profile.has_profile():
            status = "Voice profile is enrolled and speaker verification is ACTIVE."
        else:
            status = "No voice profile enrolled. Say 'enroll my voice' to set one up."
        print(f"MAX> {status}")
        self.speaker.speak(status)

    # ── Fix 6: CDII Handlers ─────────────────────────────────────────────────

    def _handle_cdii_control(self, parsed):
        """Handle 'pause YouTube on Desktop 3' style commands."""
        action = parsed.entities.get("action", "")
        app = parsed.entities.get("app", "")
        desktop_num = parsed.entities.get("desktop_num", 1)

        if not app:
            print("MAX> Which app should I control?")
            return

        msg = self.desktop_mgr.control_app_on_desktop(app, desktop_num, action)
        print(f"MAX> {msg}")
        self.speaker.speak(msg)

    def _handle_cdii_list(self, parsed):
        """Handle 'what's running on Desktop 2' style commands."""
        desktop_num = parsed.entities.get("desktop_num", 1)
        apps = self.desktop_mgr.get_apps_on_desktop(desktop_num)

        if apps:
            titles = "\n  ".join(apps[:10])  # cap at 10 for readability
            msg = f"Apps on Desktop {desktop_num}:\n  {titles}"
        else:
            msg = f"No windows found on Desktop {desktop_num}, or virtual desktop API not available."

        print(f"MAX> {msg}")
        self.speaker.speak(f"Found {len(apps)} apps on Desktop {desktop_num}.")

    # ── Fix 7: Event-Based Automation Handler ────────────────────────────────

    def _handle_event_action(self, parsed):
        """Register an event-action pair (e.g. 'shut down after this video ends')."""
        trigger = parsed.entities.get("trigger", "")
        action = parsed.entities.get("action", "")

        if not trigger or not action:
            print("MAX> Couldn't understand the event or the action.")
            return

        msg = self.event_monitor.watch(trigger, action)
        print(f"MAX> {msg}")
        self.speaker.speak(msg)

    # ── Fix 8: Chained Automation Handler ────────────────────────────────────

    def _handle_task_chain(self, parsed):
        """Execute a chain of commands sequentially."""
        steps = parsed.entities.get("steps", [])
        if not steps:
            print("MAX> No steps found in the command chain.")
            return

        print(f"MAX> Running {len(steps)}-step chain...")
        self.speaker.speak(f"Running a {len(steps)} step chain.")

        chain = TaskChain(steps, self, delay_between=1.0)
        results = chain.run()

        print(f"MAX> Chain complete. {len(results)} steps executed.")
        self.speaker.speak("Chain complete.")
