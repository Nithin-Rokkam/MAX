from max_core.core.orchestrator import Orchestrator
from max_core.input.voice_listener import VoiceListener


def main():
    orch = Orchestrator()
    listener = VoiceListener()

    def handle(text: str):
        should_exit = orch.handle_raw_command(text)
        if should_exit:
            print("MAX: Exiting voice mode.")
            raise SystemExit

    listener.listen_forever(handle)


if __name__ == "__main__":
    main()
