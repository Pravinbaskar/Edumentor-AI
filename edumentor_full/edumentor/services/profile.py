from __future__ import annotations

from typing import Dict, Any, Optional
from pathlib import Path
import json
import threading


class ProfileService:
    """Simple JSON-backed profile store.

    Stores profiles in `<repo_root>/data/profiles.json` as a mapping of user_id
    to profile dict. This is suitable for local development/demo. In
    production, replace with a proper database-backed implementation.
    """

    def __init__(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        self._data_dir = repo_root / "data"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._file = self._data_dir / "profiles.json"
        self._lock = threading.Lock()
        # ensure file exists
        if not self._file.exists():
            self._file.write_text("{}", encoding="utf-8")

    def _read_all(self) -> Dict[str, Any]:
        try:
            with self._lock:
                text = self._file.read_text(encoding="utf-8")
                if not text.strip():
                    return {}
                return json.loads(text)
        except Exception:
            return {}

    def _write_all(self, data: Dict[str, Any]) -> None:
        with self._lock:
            tmp = self._file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(self._file)

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        all_profiles = self._read_all()
        return all_profiles.get(user_id)

    def upsert_profile(self, user_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        all_profiles = self._read_all()
        all_profiles[user_id] = profile
        self._write_all(all_profiles)
        return profile
