"""Deterministic, on-demand Claude Code guard bundle generator.

The hosted unit sells customization, packaging, hashing, and immediate delivery.
Its implementation is public so buyers can inspect exactly what is generated.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import re
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


VERSION = "1.0.0-generator.1"
FIXED_ZIP_TIME = (2026, 8, 7, 0, 0, 0)
PRESET_RULES = {
    "cloud": [
        ("AWS access key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
        ("Google API key", r"\bAIza[0-9A-Za-z_-]{35}\b"),
        ("OpenAI-style key", r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    ],
    "github": [
        ("GitHub token", r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"),
    ],
    "generic": [
        ("private key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        (
            "assigned credential",
            r"(?i)\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|password)"
            r"\s*[:=]\s*['\"][^'\"\r\n]{8,}['\"]",
        ),
    ],
}


def _validated(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    project_name = payload.get("project_name", "My Project")
    if not isinstance(project_name, str) or not 1 <= len(project_name.strip()) <= 80:
        raise ValueError("project_name must be a string with 1-80 characters")
    if re.search(r"[\x00-\x1f]", project_name):
        raise ValueError("project_name cannot contain control characters")
    commit_style = payload.get("commit_style", "descriptive")
    if commit_style not in {"descriptive", "conventional"}:
        raise ValueError("commit_style must be descriptive or conventional")
    presets = payload.get("secret_presets", ["cloud", "github", "generic"])
    if not isinstance(presets, list) or not presets or len(presets) > len(PRESET_RULES):
        raise ValueError("secret_presets must be a non-empty array")
    if any(item not in PRESET_RULES for item in presets) or len(set(presets)) != len(presets):
        raise ValueError("secret_presets contains an unknown or duplicate preset")
    max_subject_length = payload.get("max_subject_length", 72)
    if not isinstance(max_subject_length, int) or not 50 <= max_subject_length <= 100:
        raise ValueError("max_subject_length must be an integer from 50 to 100")
    return {
        "project_name": project_name.strip(),
        "commit_style": commit_style,
        "secret_presets": sorted(presets),
        "max_subject_length": max_subject_length,
    }


def _guard_source(rules: list[tuple[str, str]]) -> str:
    encoded = repr(rules)
    return f'''#!/usr/bin/env python3
"""Generated Claude Code PreToolUse hook. Exit 2 blocks git commit."""
import json
import re
import subprocess
import sys

RULE_SPECS = {encoded}
RULES = [(name, re.compile(pattern)) for name, pattern in RULE_SPECS]


def main():
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("ship-guard: invalid hook input; blocking commit", file=sys.stderr)
        return 2
    command = str(event.get("tool_input", {{}}).get("command", ""))
    if not re.search(r"(?:^|[;&|]\\s*)git\\s+commit(?:\\s|$)", command):
        return 0
    diff = subprocess.run(
        ["git", "diff", "--cached", "--unified=0", "--no-color", "--diff-filter=ACMR"],
        check=False, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if diff.returncode:
        print("ship-guard: staged diff unavailable; blocking commit", file=sys.stderr)
        return 2
    added = [line[1:] for line in diff.stdout.splitlines()
             if line.startswith("+") and not line.startswith("+++")]
    findings = []
    for number, line in enumerate(added, 1):
        if "ship-guard: allow" in line.lower():
            continue
        for name, pattern in RULES:
            if pattern.search(line):
                findings.append(f"added-line {{number}}: {{name}}")
    if findings:
        print("ship-guard: BLOCKED " + ", ".join(findings[:8]), file=sys.stderr)
        return 2
    print(f"ship-guard: PASS ({{len(added)}} staged added lines scanned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _linter_source(style: str, max_length: int) -> str:
    conventional = style == "conventional"
    return f'''#!/usr/bin/env python3
import re
import sys

MAX_LENGTH = {max_length}
CONVENTIONAL = {conventional!r}
GENERIC = {{"wip", "fix", "update", "test", "tmp", "asdf"}}


def main():
    message = " ".join(sys.argv[1:]).strip()
    words = re.findall(r"[\\w'-]+", message, flags=re.UNICODE)
    if len(words) < 3 or message.casefold() in GENERIC or message.casefold().startswith("wip "):
        print("commit-message-lint: use a specific message with at least 3 words", file=sys.stderr)
        return 1
    if len(message) > MAX_LENGTH:
        print(f"commit-message-lint: subject exceeds {{MAX_LENGTH}} characters", file=sys.stderr)
        return 1
    if CONVENTIONAL and not re.match(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\\([^)]+\\))?!?: .+", message):
        print("commit-message-lint: conventional commit format required", file=sys.stderr)
        return 1
    print("commit-message-lint: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _files(options: dict) -> dict[str, bytes]:
    rules = []
    for preset in options["secret_presets"]:
        rules.extend(PRESET_RULES[preset])
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "if": "Bash(git commit *)",
                            "command": 'python "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_commit_guard.py"',
                            "timeout": 30,
                            "statusMessage": "Scanning staged changes before commit",
                        }
                    ],
                }
            ]
        }
    }
    command = f'''---
description: Review, stage, scan, and commit changes locally without pushing.
argument-hint: "<commit message>"
---

Prepare a local commit for {options["project_name"]} using `$ARGUMENTS`.
Review status and diffs, stage only relevant files, run
`python .claude/hooks/commit_message_lint.py "$ARGUMENTS"`, then run
`git commit -m "$ARGUMENTS"`. The PreToolUse hook checks staged added lines.
Never push, force-push, or open a pull request unless separately requested.
'''
    readme = f'''# {options["project_name"]} — generated Ship Guard

Generated by PinkHive x402 Ship Guard {VERSION}.

- Commit style: {options["commit_style"]}
- Maximum subject length: {options["max_subject_length"]}
- Secret presets: {", ".join(options["secret_presets"])}

Requirements: Claude Code 2.1.85+, Python 3.9+, Git. Copy `.claude` into the
repository root, merge settings if one already exists, restart Claude Code, and
run `/ship "your descriptive commit message"`.

This is a lightweight warning layer, not a complete secret scanner. It runs
locally and does not upload source, push, or create pull requests.
'''
    manifest = {
        "generator": "PinkHive x402 Ship Guard",
        "generator_version": VERSION,
        "options": options,
        "license": "MIT",
        "affiliation": "Independent; not affiliated with or endorsed by Anthropic.",
    }
    return {
        ".claude/settings.json": (json.dumps(settings, indent=2) + "\n").encode(),
        ".claude/commands/ship.md": command.encode(),
        ".claude/hooks/pre_commit_guard.py": _guard_source(rules).encode(),
        ".claude/hooks/commit_message_lint.py": _linter_source(options["commit_style"], options["max_subject_length"]).encode(),
        "README.md": readme.encode(),
        "manifest.json": (json.dumps(manifest, indent=2) + "\n").encode(),
    }


def _zip(files: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            info = ZipInfo(f"claude-ship-guard/{name}", FIXED_ZIP_TIME)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, files[name])
    return stream.getvalue()


def build_ship_guard_bundle(payload: dict) -> dict:
    options = _validated(payload)
    files = _files(options)
    archive = _zip(files)
    return {
        "product": "Claude Ship Guard — custom bundle",
        "version": VERSION,
        "options": options,
        "filename": "claude-ship-guard-custom.zip",
        "media_type": "application/zip",
        "bytes": len(archive),
        "sha256": hashlib.sha256(archive).hexdigest(),
        "files": sorted(f"claude-ship-guard/{name}" for name in files),
        "zip_base64": base64.b64encode(archive).decode("ascii"),
        "decode": "Base64-decode zip_base64 and save as claude-ship-guard-custom.zip",
    }
