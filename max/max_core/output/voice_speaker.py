"""
VoiceSpeaker — Text-to-speech output for MAX using pyttsx3.

Runs each speak() call in a fresh thread with its own pyttsx3 engine.
This is required because:
  - pyttsx3 uses COM internally on Windows (SAPI5 driver)
  - pywinauto initializes COM in MTA mode on the main thread
  - pyttsx3/SAPI5 needs STA mode — cannot share the main thread's COM state
Running in a fresh thread avoids the WinError -2147417850 crash and ensures
the engine stays alive for repeated calls throughout the session.
"""

import threading


class VoiceSpeaker:
    def __init__(self):
        self._lock = threading.Lock()
        # Test that pyttsx3 is importable at startup (fail fast)
        try:
            import pyttsx3  # noqa: F401
            self._available = True
        except ImportError:
            self._available = False
            print("MAX [VoiceSpeaker] pyttsx3 not installed — voice output disabled.")

    def speak(self, text: str):
        """Speaks `text` aloud. Non-blocking from the caller's perspective."""
        if not text or not self._available:
            return

        def _worker():
            with self._lock:   # serialize concurrent speak calls
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.setProperty("rate", 165)
                    engine.setProperty("volume", 1.0)
                    engine.say(text)
                    engine.runAndWait()
                    engine.stop()
                except Exception as e:
                    # Never let a TTS failure crash anything
                    print(f"MAX [VoiceSpeaker] speak error: {e}")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        t.join()  # wait so audio finishes before the next command prompt appears
