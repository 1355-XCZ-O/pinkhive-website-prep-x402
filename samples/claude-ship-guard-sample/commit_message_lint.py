#!/usr/bin/env python3
import re
import sys


GENERIC = {"wip", "fix", "fixes", "update", "updates", "test", "tmp", "asdf"}


def main() -> int:
    message = " ".join(sys.argv[1:]).strip()
    words = re.findall(r"[\w'-]+", message, flags=re.UNICODE)
    if len(words) < 3:
        print("commit-message-lint: message needs at least 3 words", file=sys.stderr)
        return 1
    if message.casefold() in GENERIC or message.casefold().startswith("wip "):
        print("commit-message-lint: message is too generic", file=sys.stderr)
        return 1
    if len(message) > 72:
        print("commit-message-lint: first line exceeds 72 characters", file=sys.stderr)
        return 1
    print("commit-message-lint: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
