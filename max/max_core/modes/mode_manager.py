class ModeManager:
    def __init__(self):
        self.mode = "USER"

    def activate_prime(self):
        self.mode = "PRIME"

    def deactivate_prime(self):
        self.mode = "USER"

    def current_mode(self) -> str:
        return self.mode

    def can_execute(self, intent: str) -> bool:
        restricted_prime_intents = [
            "DELETE_FILE",
            "RUN_COMMAND",
            "SHUTDOWN",
            "KILL_PROCESS",
            # "CLOSE_APP_OR_FOLDER",  # treat as sensitive for now
        ]
        if intent in restricted_prime_intents and self.mode != "PRIME":
            return False
        return True
