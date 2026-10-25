"""R7 cost per batch (``notes/siting_production_plan.md`` section 5 item 7): every invocation of
``experiments/r7_siting.py`` and ``experiments/r7_search.py`` appends one row to ``cost.jsonl`` in
its ``--out-dir``::

    {"stage", "start", "end", "start_epoch", "end_epoch", "wall_h", "instance", "usd_per_h", "usd",
     "batch", "script", "status", "dry_run", "host", "pid", "argv"}

``instance`` and ``usd_per_h`` come from the environment (``R7_INSTANCE``, ``R7_USD_PER_H``;
defaults ``r7i.4xlarge`` and 1.0584 USD/h, the us-east-2 on-demand price of 2026-10-21);
``batch`` from ``R7_BATCH`` (the production lanes set it to the batch number of plan section 2.2;
``None`` otherwise).  ``usd = wall_h x usd_per_h`` is the price of the instance for the wall time of
the process: lanes that run side by side on one instance therefore each carry the full price, and
:func:`summarise` reports both the plain sum and the union of the time intervals per batch (the
instance hours actually paid while the lanes ran; overlaps counted once).  Idle time between lanes
and the probe batches are not in the file.

Fixer pass (review of 2026-10-21):

* a ``start`` row (``"event": "start"``) is appended when the invocation begins, the full row
  (``"event": "end"``) when it ends; :func:`summarise` pairs them by ``(host, pid, start_epoch)``
  and counts a start without an end as ``unfinished`` (a hard kill: SIGKILL / OOM / instance
  stop); its interval runs to now while the pid is alive on this host, else it is empty and
  only counted, so the table says that hours are missing;
* :meth:`CostLog.install_signal_handlers` makes SIGTERM (``run_lanes.sh stop``) and SIGHUP
  (``tmux kill-session``) write the end row (status ``killed: SIGTERM``) and then exit at once
  with ``128 + signum``, as the default handlers would (a ``finally`` would wait for the
  Gurobi solves in flight);
* the laptop analysis (``--stage analyse`` / ``report``) writes no row (``enabled=False``), and
  rows without ``R7_BATCH`` are left out of ``total`` when batched rows exist (shown as
  ``None (unbatched, not in total)``).

English only.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

DEFAULT_INSTANCE = "r7i.4xlarge"
DEFAULT_USD_PER_H = 1.0584
COST_FILE = "cost.jsonl"


def instance_price() -> Tuple[str, float]:
    """``(instance, usd_per_h)`` from ``R7_INSTANCE`` / ``R7_USD_PER_H`` (defaults r7i.4xlarge, 1.0584)."""
    inst = os.environ.get("R7_INSTANCE") or DEFAULT_INSTANCE
    raw = os.environ.get("R7_USD_PER_H")
    try:
        usd = float(raw) if raw not in (None, "") else DEFAULT_USD_PER_H
    except ValueError:
        usd = DEFAULT_USD_PER_H
    return inst, usd


def _iso(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


#: signals that end a lane (``run_lanes.sh stop`` sends SIGTERM, ``tmux kill-session`` SIGHUP)
EXIT_SIGNALS = ("SIGTERM", "SIGHUP")


class CostLog:
    """One invocation: a ``start`` row when it is created, ``finish(status)`` once at the end (from
    a ``finally``, or from the SIGTERM / SIGHUP handler of :meth:`install_signal_handlers`); the
    rows are appended to ``<out_dir>/cost.jsonl``.  ``enabled=False`` writes nothing (the laptop
    analysis stages)."""

    def __init__(self, out_dir: str, stage: str, script: str, dry_run: bool = False,
                 argv: Optional[Sequence[str]] = None, enabled: bool = True) -> None:
        self.path = os.path.join(out_dir, COST_FILE)
        self.stage = str(stage)
        self.script = script
        self.dry_run = bool(dry_run)
        self.argv = list(sys.argv[1:] if argv is None else argv)
        self.t0 = time.time()
        self.done = not enabled
        self.enabled = bool(enabled)
        self._prev_handlers: Dict[int, Any] = {}
        if self.enabled:
            self._append(self._row(None, "running", event="start"))

    def _row(self, t1: Optional[float], status: str, event: str = "end") -> Dict[str, Any]:
        inst, usd_h = instance_price()
        wall_h = None if t1 is None else max(0.0, t1 - self.t0) / 3600.0
        return {"event": event, "stage": self.stage, "start": _iso(self.t0), "end": None if t1 is None else _iso(t1),
                "start_epoch": round(self.t0, 3), "end_epoch": None if t1 is None else round(t1, 3),
                "wall_h": None if wall_h is None else round(wall_h, 6), "instance": inst, "usd_per_h": usd_h,
                "usd": None if wall_h is None else round(wall_h * usd_h, 6), "batch": os.environ.get("R7_BATCH") or None,
                "script": self.script, "status": str(status), "dry_run": self.dry_run, "host": socket.gethostname(),
                "pid": os.getpid(), "argv": self.argv}

    def _append(self, row: Dict[str, Any]) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row) + "\n")
        except OSError:
            pass

    def finish(self, status: str = "ok") -> Optional[Dict[str, Any]]:
        if self.done:
            self.restore_signal_handlers()
            return None
        self.done = True
        row = self._row(time.time(), status)
        self._append(row)
        self.restore_signal_handlers()
        return row

    # -- signals ---------------------------------------------------------------------
    def _on_signal(self, signum: int, _frame: Any) -> None:
        name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
        self.finish(f"killed: {name}")
        os._exit(128 + int(signum))           # as the default handler: no wait for the solves in flight

    def install_signal_handlers(self) -> List[str]:
        """SIGTERM / SIGHUP write the end row and exit with ``128 + signum`` (main thread only;
        elsewhere nothing is installed).  :meth:`finish` restores the previous handlers.
        Returns the names of the signals handled."""
        out: List[str] = []
        if not self.enabled:
            return out
        for name in EXIT_SIGNALS:
            sig = getattr(signal, name, None)
            if sig is None:
                continue
            try:
                self._prev_handlers[int(sig)] = signal.signal(sig, self._on_signal)
                out.append(name)
            except (ValueError, OSError, RuntimeError):     # not the main thread
                continue
        return out

    def restore_signal_handlers(self) -> None:
        for sig, h in list(self._prev_handlers.items()):
            try:
                signal.signal(sig, h if h is not None else signal.SIG_DFL)
            except (ValueError, OSError, RuntimeError):
                pass
        self._prev_handlers = {}


def load(path: str, events: bool = False) -> List[Dict[str, Any]]:
    """The rows of ``cost.jsonl``: the end rows (one per finished invocation; rows written before
    the fixer pass have no ``event`` and count as end rows), with ``events`` the start rows too."""
    if os.path.isdir(path):
        path = os.path.join(path, COST_FILE)
    out: List[Dict[str, Any]] = []
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if events or r.get("event", "end") != "start":
                out.append(r)
    return out


def _pid_alive(host: Any, pid: Any) -> bool:
    if str(host) != socket.gethostname():
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def unfinished(path: str, now: Optional[float] = None) -> List[Dict[str, Any]]:
    """Start rows without an end row (same host, pid and start): a hard kill (SIGKILL, OOM, an
    instance stop) or a process still running.  ``end_epoch`` = now while the pid is alive on
    this host, else the start (the lost hours are unknown; the row is only counted)."""
    rows = load(path, events=True)
    ends = {(r.get("host"), r.get("pid"), r.get("start_epoch")) for r in rows if r.get("event", "end") != "start"}
    out = []
    t = time.time() if now is None else float(now)
    for r in rows:
        if r.get("event") != "start" or (r.get("host"), r.get("pid"), r.get("start_epoch")) in ends:
            continue
        alive = _pid_alive(r.get("host"), r.get("pid"))
        st = float(r.get("start_epoch") or 0.0)
        end = t if alive else st
        wall_h = max(0.0, end - st) / 3600.0
        out.append(dict(r, end_epoch=end, wall_h=wall_h, usd=wall_h * float(r.get("usd_per_h") or 0.0),
                        status="running" if alive else "unfinished (no end row: hard kill?)"))
    return out


def _union_h(intervals: Sequence[Tuple[float, float]]) -> float:
    tot, cur = 0.0, None
    for a, b in sorted(intervals):
        if cur is None or a > cur[1]:
            if cur is not None:
                tot += cur[1] - cur[0]
            cur = [a, b]
        else:
            cur[1] = max(cur[1], b)
    if cur is not None:
        tot += cur[1] - cur[0]
    return tot / 3600.0


def summarise(path: str, include_dry_run: bool = False) -> Dict[str, Any]:
    """Per batch (``R7_BATCH``; ``None`` = unbatched): number of invocations, stages, the plain sum
    of ``wall_h`` / ``usd`` and the union of the time intervals (instance hours with overlapping
    lanes counted once) priced at each row's ``usd_per_h`` (the largest one when a batch mixes
    prices).  ``total`` sums the batches."""
    rows = [r for r in load(path) if include_dry_run or not r.get("dry_run")]
    open_rows = [r for r in unfinished(path) if include_dry_run or not r.get("dry_run")]
    by: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows + open_rows:
        by.setdefault(str(r.get("batch")), []).append(r)
    batched = any(b != "None" for b in by)
    out: Dict[str, Any] = {"batches": {}, "n_rows": len(rows), "n_unfinished": len(open_rows)}
    tot = {"wall_h_sum": 0.0, "usd_sum": 0.0, "instance_h": 0.0, "usd_instance": 0.0}
    for b, rs in sorted(by.items(), key=lambda kv: (kv[0] == "None", kv[0])):
        iv = [(float(r.get("start_epoch") or 0.0), float(r.get("end_epoch") or 0.0)) for r in rs]
        inst_h = _union_h(iv)
        price = max(float(r.get("usd_per_h") or 0.0) for r in rs)
        rec = {"n": len(rs), "stages": sorted({str(r.get("stage")) for r in rs}),
               "instances": sorted({str(r.get("instance")) for r in rs}),
               "wall_h_sum": sum(float(r.get("wall_h") or 0.0) for r in rs),
               "usd_sum": sum(float(r.get("usd") or 0.0) for r in rs),
               "instance_h": inst_h, "usd_instance": inst_h * price,
               "failed": sum(1 for r in rs if str(r.get("status", "ok")) not in ("ok", "running")
                             and not str(r.get("status", "")).startswith("unfinished")),
               "unfinished": sum(1 for r in rs if r.get("event") == "start"),
               "in_total": not (batched and b == "None")}
        out["batches"][b] = rec
        if rec["in_total"]:
            for k in tot:
                tot[k] += rec[k]
    out["total"] = tot
    return out


def summary_lines(path: str) -> List[str]:
    """Markdown lines of the cost table (empty list when there is no ``cost.jsonl``)."""
    s = summarise(path)
    if not s["n_rows"] and not s.get("n_unfinished"):
        return []
    lines = ["## Cost per batch (`cost.jsonl`; instance hours = union of the lane intervals)", "",
             "| batch | invocations | stages | instance | wall h (sum) | USD (sum) | instance h | USD (instance h) | failed "
             "| unfinished |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for b, r in s["batches"].items():
        name = b if r.get("in_total", True) else f"{b} (unbatched, not in total)"
        lines.append(f"| {name} | {r['n']} | {', '.join(r['stages'])} | {', '.join(r['instances'])} | {r['wall_h_sum']:.2f} | "
                     f"{r['usd_sum']:.2f} | {r['instance_h']:.2f} | {r['usd_instance']:.2f} | {r['failed']} | "
                     f"{r.get('unfinished', 0)} |")
    t = s["total"]
    lines.append(f"| total | {s['n_rows']} | | | {t['wall_h_sum']:.2f} | {t['usd_sum']:.2f} | {t['instance_h']:.2f} | "
                 f"{t['usd_instance']:.2f} | | {s.get('n_unfinished', 0)} |")
    if s.get("n_unfinished"):
        lines += ["", f"{s['n_unfinished']} invocation(s) have a start row but no end row (hard kill or still running): "
                      "their hours are missing from the sums unless the process is alive on this host."]
    return lines + [""]


if __name__ == "__main__":
    print(json.dumps(summarise(sys.argv[1] if len(sys.argv) > 1 else "."), indent=1))
