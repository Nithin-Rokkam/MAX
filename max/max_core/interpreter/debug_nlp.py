import sys
from .command_parser import CommandParser


def format_command_result(parsed):
    return {
        "intent": parsed.intent,
        "entities": parsed.entities,
    }


def run_samples():
    parser = CommandParser()
    samples = [
        "open chrome",
        "opne gogle crome",
        "launch google chrome on desktop",
        "bro can you creat text file notes in test on desktop please",
        "make text file data in reports folder on documents",
        "create folder test on desktop",
        "make directory projects in documents",
        "delete notes in test on desktop",
        "remove data in reports on documents",
        "notify me after 10 minutes",
        "set timer for 5 min",
        "enter prime",
        "enter prime secret phrase here",
        "exit prime",
        "close notepad",
        "set root C:/Users/Nithin/Desktop",
        "bye",
        "",
    ]

    for s in samples:
        parsed = parser.parse(s)
        print("INPUT :", repr(s))
        print("OUTPUT:", format_command_result(parsed))
        print("-" * 40)


def run_single(text: str):
    parser = CommandParser()
    parsed = parser.parse(text)
    print("INPUT :", repr(text))
    print("OUTPUT:", {
        "intent": parsed.intent,
        "entities": parsed.entities,
    })


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        run_single(cmd)
    else:
        run_samples()
