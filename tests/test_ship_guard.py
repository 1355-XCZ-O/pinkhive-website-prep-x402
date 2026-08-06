import base64
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from app.ship_guard import build_ship_guard_bundle


class ShipGuardBundleTests(unittest.TestCase):
    def test_deterministic_custom_bundle(self):
        payload = {
            "project_name": "Acme Docs",
            "commit_style": "conventional",
            "secret_presets": ["github", "generic"],
            "max_subject_length": 60,
        }
        first = build_ship_guard_bundle(payload)
        second = build_ship_guard_bundle(payload)
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertEqual(first["zip_base64"], second["zip_base64"])
        with ZipFile(io.BytesIO(base64.b64decode(first["zip_base64"]))) as archive:
            names = archive.namelist()
            self.assertIn("claude-ship-guard/.claude/settings.json", names)
            self.assertIn("claude-ship-guard/.claude/hooks/pre_commit_guard.py", names)
            manifest = json.loads(archive.read("claude-ship-guard/manifest.json"))
            self.assertEqual(manifest["options"], payload | {"secret_presets": ["generic", "github"]})

    def test_generated_hook_blocks_likely_secret(self):
        result = build_ship_guard_bundle({"project_name": "Hook Test"})
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            with ZipFile(io.BytesIO(base64.b64decode(result["zip_base64"]))) as archive:
                archive.extractall(root)
            guard = root / "claude-ship-guard" / ".claude" / "hooks" / "pre_commit_guard.py"
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "secret.env").write_text("api_key='abcdefghijklmnop1234'\n", encoding="utf-8")
            subprocess.run(["git", "add", "secret.env"], cwd=root, check=True)
            event = json.dumps({"tool_input": {"command": "git commit -m test"}})
            blocked = subprocess.run([sys.executable, str(guard)], cwd=root, input=event, text=True, capture_output=True)
            self.assertEqual(blocked.returncode, 2)
            self.assertIn("BLOCKED", blocked.stderr)

    def test_input_limits(self):
        with self.assertRaisesRegex(ValueError, "project_name"):
            build_ship_guard_bundle({"project_name": ""})
        with self.assertRaisesRegex(ValueError, "commit_style"):
            build_ship_guard_bundle({"project_name": "A", "commit_style": "anything"})
        with self.assertRaisesRegex(ValueError, "secret_presets"):
            build_ship_guard_bundle({"project_name": "A", "secret_presets": ["unknown"]})


if __name__ == "__main__":
    unittest.main()
