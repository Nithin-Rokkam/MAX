"""
VoiceProfileManager — Speaker Verification for MAX
Uses resemblyzer to create and verify a user voice embedding.

Install: pip install resemblyzer
"""

from pathlib import Path
import numpy as np

# Lazy import so system still starts even if resemblyzer not installed
try:
    from resemblyzer import VoiceEncoder, preprocess_wav
    RESEMBLYZER_AVAILABLE = True
except ImportError:
    RESEMBLYZER_AVAILABLE = False


PROFILE_PATH = Path("data/voice_profile.npy")
SIMILARITY_THRESHOLD = 0.75  # Cosine similarity — tune as needed


class VoiceProfileManager:
    def __init__(self):
        self._encoder = None
        PROFILE_PATH.parent.mkdir(exist_ok=True)

    @property
    def encoder(self):
        if self._encoder is None and RESEMBLYZER_AVAILABLE:
            self._encoder = VoiceEncoder()
        return self._encoder

    def is_available(self) -> bool:
        return RESEMBLYZER_AVAILABLE

    def has_profile(self) -> bool:
        return PROFILE_PATH.exists()

    def enroll(self, audio_file_path: str) -> bool:
        """
        Enroll a speaker by computing and saving their embedding from a WAV file.
        Returns True on success.
        """
        if not RESEMBLYZER_AVAILABLE:
            print("MAX> resemblyzer not installed. Run: pip install resemblyzer")
            return False
        try:
            wav = preprocess_wav(audio_file_path)
            embedding = self.encoder.embed_utterance(wav)
            np.save(str(PROFILE_PATH), embedding)
            print(f"MAX> Voice profile saved to {PROFILE_PATH}")
            return True
        except Exception as e:
            print(f"MAX> Enrollment failed: {e}")
            return False

    def enroll_from_array(self, audio_array: np.ndarray, sample_rate: int = 16000) -> bool:
        """
        Enroll directly from a numpy audio array (for live recording).
        """
        if not RESEMBLYZER_AVAILABLE:
            return False
        try:
            from resemblyzer import preprocess_wav
            import io, soundfile as sf

            # Convert to WAV bytes then preprocess
            buf = io.BytesIO()
            sf.write(buf, audio_array, sample_rate, format="WAV")
            buf.seek(0)
            wav = preprocess_wav(buf)
            embedding = self.encoder.embed_utterance(wav)
            np.save(str(PROFILE_PATH), embedding)
            return True
        except Exception as e:
            print(f"MAX> Enrollment from array failed: {e}")
            return False

    def verify(self, audio_data: bytes) -> bool:
        """
        Verify if the given audio matches the enrolled profile.
        Returns True if the speaker matches (similarity >= threshold).
        """
        if not RESEMBLYZER_AVAILABLE:
            # If library not available, skip verification (fail open)
            return True

        if not self.has_profile():
            # No profile enrolled yet — skip verification (fail open)
            return True

        try:
            import io
            import soundfile as sf
            from resemblyzer import preprocess_wav

            stored_embedding = np.load(str(PROFILE_PATH))

            # Parse raw audio bytes to numpy
            buf = io.BytesIO(audio_data)
            wav = preprocess_wav(buf)
            new_embedding = self.encoder.embed_utterance(wav)

            # Cosine similarity
            similarity = float(
                np.dot(stored_embedding, new_embedding) /
                (np.linalg.norm(stored_embedding) * np.linalg.norm(new_embedding) + 1e-9)
            )
            print(f"MAX [voice-verify] similarity = {similarity:.3f} (threshold={SIMILARITY_THRESHOLD})")
            return similarity >= SIMILARITY_THRESHOLD

        except Exception as e:
            print(f"MAX> Voice verification error (failing open): {e}")
            return True  # fail open so system still works if library has issues
