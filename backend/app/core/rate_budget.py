"""
Trackea cuántos requests ya se consumieron hoy contra cada API, persistido
en un archivo local simple. Permite que los scripts de carga incremental
sepan cuánta cuota les queda sin depender de que vos lo recuerdes.
"""

import json
from datetime import date
from pathlib import Path

BUDGET_FILE = Path(__file__).parent.parent.parent / ".rate_budget.json"


class RateBudget:

    def __init__(self, provider: str, daily_limit: int) -> None:
        self.provider = provider
        self.daily_limit = daily_limit

    def _load(self) -> dict:
        if not BUDGET_FILE.exists():
            return {}
        try:
            return json.loads(BUDGET_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict) -> None:
        BUDGET_FILE.write_text(json.dumps(data, indent=2))

    def _today_key(self) -> str:
        return f"{self.provider}:{date.today().isoformat()}"

    def used_today(self) -> int:
        data = self._load()
        return data.get(self._today_key(), 0)

    def remaining_today(self) -> int:
        return max(0, self.daily_limit - self.used_today())

    def record_usage(self, count: int) -> None:
        data = self._load()
        key = self._today_key()
        data[key] = data.get(key, 0) + count
        self._save(data)