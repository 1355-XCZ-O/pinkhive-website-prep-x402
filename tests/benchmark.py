import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from app.core import build_site_bundle

payload = json.loads((Path(__file__).parents[1] / "examples" / "request.json").read_text(encoding="utf-8"))
durations = []
for _ in range(100):
    started = time.perf_counter()
    build_site_bundle(payload)
    durations.append((time.perf_counter() - started) * 1000)
print(json.dumps({"runs": 100, "median_ms": statistics.median(durations), "p95_ms": sorted(durations)[94], "mean_ms": statistics.mean(durations)}, indent=2))
