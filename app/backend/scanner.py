import os
import json
import time
import shutil
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import psutil


class DeviceScanner:
    """Simulated vulnerability scanner suitable for mobile constraints.

    The scanner performs fast heuristic checks and returns a findings dict with:
      - suspicious_processes: list[str]
      - suspicious_files: list[str]
      - recommendations: list[str]
      - threat_score: float (0..1)
    """

    def __init__(self, user_data_dir: str) -> None:
        self.user_data_dir = user_data_dir
        self.quarantine_dir = os.path.join(self.user_data_dir, "quarantine")
        os.makedirs(self.quarantine_dir, exist_ok=True)
        self._lock = threading.Lock()
        self._current_thread: Optional[threading.Thread] = None

    def is_scanning(self) -> bool:
        with self._lock:
            return self._current_thread is not None and self._current_thread.is_alive()

    def start_scan(
        self,
        on_progress: Optional[Callable[[float, str], None]] = None,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        if self.is_scanning():
            return

        def run() -> None:
            steps = [
                ("Enumerating processes", self._check_processes),
                ("Scanning storage for risky files", self._check_files),
                ("Applying heuristic analysis", self._heuristics),
            ]
            findings: Dict[str, Any] = {
                "suspicious_processes": [],
                "suspicious_files": [],
                "recommendations": [],
                "threat_score": 0.0,
                "started_at": datetime.utcnow().isoformat(),
                "ended_at": None,
            }

            for idx, (label, func) in enumerate(steps, start=1):
                try:
                    if on_progress:
                        on_progress(idx / len(steps), label)
                    result = func()
                    # Merge
                    for key, value in result.items():
                        if isinstance(value, list):
                            findings.setdefault(key, []).extend(value)
                        else:
                            findings[key] = value
                    time.sleep(0.3)
                except Exception:
                    pass

            # Recommendations
            if findings["suspicious_processes"] or findings["suspicious_files"]:
                findings["recommendations"].append(
                    "Consider terminating unknown processes and removing suspicious files."
                )
                findings["recommendations"].append(
                    "Enable automatic scans and keep apps updated from trusted stores."
                )

            # Threat score
            num_items = len(findings["suspicious_processes"]) + len(findings["suspicious_files"])
            findings["threat_score"] = min(1.0, num_items / 10.0)
            findings["ended_at"] = datetime.utcnow().isoformat()

            if on_complete:
                on_complete(findings)

            with self._lock:
                self._current_thread = None

        t = threading.Thread(target=run, daemon=True)
        with self._lock:
            self._current_thread = t
        t.start()

    def _check_processes(self) -> Dict[str, Any]:
        suspicious_keywords = ["keylogger", "miner", "rat", "spy", "sniff", "ddos"]
        suspicious: List[str] = []
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if any(k in name for k in suspicious_keywords):
                    suspicious.append(f"{name} (pid {proc.pid})")
            except Exception:
                continue
        return {"suspicious_processes": suspicious}

    def _check_files(self) -> Dict[str, Any]:
        suspicious_extensions = [".apk", ".exe", ".sh", ".bat"]
        suspicious: List[str] = []
        candidate_dirs = [
            os.path.expanduser("~/Downloads"),
            os.path.join(self.user_data_dir, "Downloads"),
        ]
        for d in candidate_dirs:
            if not os.path.isdir(d):
                continue
            for root, _dirs, files in os.walk(d):
                for f in files:
                    path = os.path.join(root, f)
                    if any(f.lower().endswith(ext) for ext in suspicious_extensions):
                        suspicious.append(path)
                        if len(suspicious) >= 50:
                            break
        return {"suspicious_files": suspicious}

    def _heuristics(self) -> Dict[str, Any]:
        return {"recommendations": ["No critical issues found in heuristic phase."]}

    def isolate_threat(self, path: str) -> Optional[str]:
        try:
            if not os.path.exists(path):
                return None
            base = os.path.basename(path)
            target = os.path.join(self.quarantine_dir, base)
            shutil.move(path, target)
            return target
        except Exception:
            return None