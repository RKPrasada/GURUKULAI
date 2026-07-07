from __future__ import annotations
"""
GCS-backed persistence for Cloud Run.

Cloud Run containers have an ephemeral filesystem — every cold start
loses vidyabot.db and data/. This module syncs both to a GCS bucket so
data survives restarts and scale-to-zero events.

Behaviour:
  - GCS_DATA_BUCKET not set → all functions are no-ops (local dev safe)
  - On startup  → download db + data/ from GCS (restore_from_gcs)
  - On shutdown → upload db + data/ to GCS   (backup_to_gcs)
  - Background  → periodic sync every SYNC_INTERVAL_SECS (start_background_sync)

GCS layout inside the bucket:
  db/vidyabot.db          ← the SQLite file
  data/<relative path>    ← mirrors the local data/ directory tree

Exclusions (large, rebuildable):
  data/chroma_db/         ← RAG vector store; rebuilt as NAGA approves notes
  data/mock_banks/        ← regenerated every Saturday by the scheduler
"""

import logging
import os
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECS = 300  # 5 minutes

# Paths relative to project root
_ROOT      = Path(__file__).parent.parent
_DATA_DIR  = _ROOT / "data"
_BUCKET    = os.getenv("GCS_DATA_BUCKET", "")

# Subdirectories skipped during sync (large, rebuildable)
_SKIP_DIRS = {"chroma_db", "mock_banks"}


def _client():
    from google.cloud import storage  # type: ignore
    return storage.Client()


def _is_enabled() -> bool:
    return bool(_BUCKET)


# ── Upload helpers ──────────────────────────────────────────────────────────────

def _upload_file(bucket, local_path: Path, blob_name: str) -> None:
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path))


def _download_file(bucket, blob_name: str, local_path: Path) -> bool:
    """Download blob to local_path. Returns False if blob doesn't exist."""
    blob = bucket.blob(blob_name)
    if not blob.exists():
        return False
    local_path.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(local_path))
    return True


# ── Public API ──────────────────────────────────────────────────────────────────

def backup_to_gcs(db_path: str = "vidyabot.db") -> None:
    """Upload the SQLite DB and data/ directory to GCS."""
    if not _is_enabled():
        return
    try:
        bkt = _client().bucket(_BUCKET)

        # DB file
        db = Path(db_path)
        if db.exists():
            _upload_file(bkt, db, f"db/{db.name}")
            logger.info("Persistence: uploaded %s → gs://%s/db/%s", db, _BUCKET, db.name)

        # data/ directory (excluding large rebuildable subdirs)
        uploaded = 0
        for local in _DATA_DIR.rglob("*"):
            if not local.is_file():
                continue
            if any(part in _SKIP_DIRS for part in local.parts):
                continue
            rel = local.relative_to(_ROOT)
            _upload_file(bkt, local, str(rel))
            uploaded += 1
        logger.info("Persistence: uploaded %d data files → gs://%s/data/", uploaded, _BUCKET)

    except Exception as e:
        logger.error("Persistence: backup_to_gcs failed: %s", e)


def restore_from_gcs(db_path: str = "vidyabot.db") -> None:
    """Download the SQLite DB and data/ directory from GCS."""
    if not _is_enabled():
        return
    try:
        bkt = _client().bucket(_BUCKET)

        # DB file
        db = Path(db_path)
        if _download_file(bkt, f"db/{db.name}", db):
            logger.info("Persistence: restored %s from GCS", db)
        else:
            logger.info("Persistence: no DB snapshot in GCS yet — starting fresh")

        # data/ directory
        restored = 0
        for blob in bkt.list_blobs(prefix="data/"):
            if blob.name.endswith("/"):
                continue
            # Skip excluded dirs
            parts = Path(blob.name).parts
            if len(parts) > 1 and parts[1] in _SKIP_DIRS:
                continue
            local = _ROOT / blob.name
            local.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(local))
            restored += 1
        logger.info("Persistence: restored %d data files from GCS", restored)

    except Exception as e:
        logger.error("Persistence: restore_from_gcs failed: %s", e)


def start_background_sync(db_path: str = "vidyabot.db") -> None:
    """Start a daemon thread that backs up to GCS every SYNC_INTERVAL_SECS."""
    if not _is_enabled():
        return

    def _loop():
        while True:
            time.sleep(SYNC_INTERVAL_SECS)
            logger.info("Persistence: periodic sync starting")
            backup_to_gcs(db_path)

    t = threading.Thread(target=_loop, daemon=True, name="gcs-sync")
    t.start()
    logger.info("Persistence: background sync started (interval=%ds bucket=%s)", SYNC_INTERVAL_SECS, _BUCKET)
