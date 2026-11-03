#!/usr/bin/env python3
"""Exit 0 when every failed gate of an R8 dry run is in the allowed list, else 3.

Used by the 64-rider fallback chain (author's decision, 2026-10-28): at 64 riders / 320 orders a
failed swap gate (median open site below 3 swaps per evening) no longer stops the search, because
there is no larger approved fleet; the per-site table reports the idle sites. A failed cost gate
(cell time or worker memory) still stops the chain for the author to decide.

    python3 r8_gate_ok.py outputs/r8_k15_n64/dryrun.json median_site_swaps
"""
import json
import sys

path, allowed = sys.argv[1], set(sys.argv[2:])
d = json.load(open(path, encoding="utf-8"))
bad = [k for k, g in d.get("gates", {}).items() if not g.get("ok")]
print(f"dry run {path}: failed gates {bad}, allowed {sorted(allowed)}", flush=True)
sys.exit(0 if set(bad) <= allowed else 3)
