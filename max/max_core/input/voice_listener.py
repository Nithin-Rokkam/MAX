import speech_recognition as sr
from max_core.security.voice_profile_manager import VoiceProfileManager


class VoiceListener:
    def __init__(self, verify_speaker: bool = True):
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        self.profile_manager = VoiceProfileManager()
        self.verify_speaker = verify_speaker

    def listen_forever(self, callback):
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            print("MAX: Voice mode enabled. Speak your commands.")
            if self.verify_speaker and self.profile_manager.has_profile():
                print("MAX: Speaker verification is ACTIVE.")
            elif self.verify_speaker and not self.profile_manager.has_profile():
                print("MAX: No voice profile enrolled. Say 'enroll my voice' to set one up.")
            else:
                print("MAX: Speaker verification is DISABLED.")

            while True:
                print("...listening...")
                audio = self.recognizer.listen(source)

                try:
                    text = self.recognizer.recognize_google(audio)
                    text = text.strip()
                    if not text:
                        continue

                    # ── Speaker verification ─────────────────────────────
                    if (
                        self.verify_speaker
                        and self.profile_manager.is_available()
                        and self.profile_manager.has_profile()
                        and "enroll" not in text.lower()
                    ):
                        audio_data = audio.get_wav_data()
                        if not self.profile_manager.verify(audio_data):
                            print("MAX> Voice not recognized. Command ignored.")
                            continue

                    print(f"\nyou (voice)> {text}")
                    callback(text)

                except sr.UnknownValueError:
                    print("MAX> I couldn't understand that.")
                except sr.RequestError as e:
                    print(f"MAX> Speech recognition error: {e}")

    def record_sample(self, duration_seconds: int = 5) -> bytes:
        """Record a voice sample and return raw WAV bytes (for enrollment)."""
        print(f"MAX> Recording for {duration_seconds} seconds... Please speak.")
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=duration_seconds + 2, phrase_time_limit=duration_seconds)
                print("MAX> Recording complete.")
                return audio.get_wav_data()
            except sr.WaitTimeoutError:
                print("MAX> No speech detected during recording.")
                return b""
