"""
Lista persistente de fixture external_ids que la API-Football devuelve
con datos de equipos incorrectos (fixture ID mal indexado del lado del
proveedor). Confirmado reproducible en múltiples corridas — no tiene
sentido seguir reintentándolos, solo queman cuota sin resultado posible.
"""

import json
from pathlib import Path

BAD_FIXTURES_FILE = Path(__file__).parent.parent.parent / ".bad_fixtures.json"


def load_bad_fixtures() -> set[str]:
    if not BAD_FIXTURES_FILE.exists():
        return set()
    try:
        return set(json.loads(BAD_FIXTURES_FILE.read_text()))
    except (json.JSONDecodeError, OSError):
        return set()


def mark_bad_fixture(external_id: str) -> None:
    bad = load_bad_fixtures()
    bad.add(external_id)
    BAD_FIXTURES_FILE.write_text(json.dumps(sorted(bad), indent=2))