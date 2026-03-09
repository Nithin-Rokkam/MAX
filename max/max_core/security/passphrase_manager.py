import hashlib
import json
from pathlib import Path


class PassphraseManager:
    def __init__(self):
        self.passfile = Path("data/passphrase.json")
        self.passfile.parent.mkdir(exist_ok=True)
        if not self.passfile.exists():
            self.passfile.write_text(json.dumps({"hash": None}))

    def set_passphrase(self, phrase: str):
        hashed = hashlib.sha256(phrase.encode()).hexdigest()
        self.passfile.write_text(json.dumps({"hash": hashed}))
        return True

    def has_passphrase(self) -> bool:
        data = json.loads(self.passfile.read_text())
        return bool(data.get("hash"))

    def verify(self, phrase: str) -> bool:
        data = json.loads(self.passfile.read_text())
        stored = data.get("hash")
        if not stored:
            return False
        hashed = hashlib.sha256(phrase.encode()).hexdigest()
        return stored == hashed
