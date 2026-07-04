from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

from security.pii_scrubber import PIIScrubber

_scrubber = PIIScrubber()


class AuditLogger:
    def __init__(self, log_path: str | None = None):
        self.log_path = Path(log_path or os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl"))
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._prev_hash, self._next_seq = self._init_state()

    def _init_state(self) -> tuple[str, int]:
        """Return (last_entry_hash, next_sequence_id) from existing log."""
        genesis = hashlib.sha256(b"GENESIS").hexdigest()
        if not self.log_path.exists():
            return genesis, 0
        last_hash = genesis
        last_seq = -1
        with open(self.log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                last_hash = entry.get("entry_hash", genesis)
                last_seq = entry.get("sequence_id", last_seq)
        return last_hash, last_seq + 1

    def _append(self, entry: dict) -> None:
        entry["sequence_id"] = self._next_seq
        entry["prev_hash"] = self._prev_hash
        raw = json.dumps(entry, sort_keys=True)
        entry["entry_hash"] = hashlib.sha256(raw.encode()).hexdigest()
        self._prev_hash = entry["entry_hash"]
        self._next_seq += 1
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def log_interaction(self, student_id: str, input_text: str, output_text: str) -> None:
        self._append({
            "timestamp": datetime.utcnow().isoformat(),
            "entry_type": "interaction",
            "student_id": hashlib.sha256(student_id.encode()).hexdigest()[:16],
            "input_length": len(input_text),
            "output_length": len(output_text),
        })

    def log_threat(self, student_id: str, raw_input: str, threat_type: str) -> None:
        safe_preview, _ = _scrubber.scrub(raw_input[:50])
        self._append({
            "timestamp": datetime.utcnow().isoformat(),
            "entry_type": "security_event",
            "student_id": hashlib.sha256(student_id.encode()).hexdigest()[:16],
            "threat_type": threat_type,
            "input_preview": safe_preview,
        })

    def log_auth_event(self, student_id: str, event_type: str) -> None:
        self._append({
            "timestamp": datetime.utcnow().isoformat(),
            "entry_type": "auth_event",
            "student_id": hashlib.sha256(student_id.encode()).hexdigest()[:16],
            "event": event_type,
        })

    def verify_chain(self) -> bool:
        """
        Returns True only if the entire log is intact:
        - SHA-256 chain is unbroken
        - sequence_ids are consecutive with no gaps (detects truncation)
        """
        if not self.log_path.exists():
            return True
        prev_hash = hashlib.sha256(b"GENESIS").hexdigest()
        expected_seq = 0
        with open(self.log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                stored_hash = entry.pop("entry_hash")

                # Sequence gap = truncation attack
                if entry.get("sequence_id") != expected_seq:
                    return False
                expected_seq += 1

                if entry.get("prev_hash") != prev_hash:
                    return False
                raw = json.dumps(entry, sort_keys=True)
                computed = hashlib.sha256(raw.encode()).hexdigest()
                if computed != stored_hash:
                    return False
                prev_hash = stored_hash
        return True
