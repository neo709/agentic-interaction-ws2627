"""Konfiguration aus der .env-Datei und den Umgebungsvariablen lesen."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_MAX_STEPS = 10


class ConfigError(Exception):
    """Eine Einstellung fehlt oder ist ungültig."""


@dataclass(frozen=True)
class Config:
    base_url: str        # OPENAI_BASE_URL – Endpunkt des Modells
    model: str           # MODEL
    api_key: str         # OPENAI_API_KEY
    data_base_url: str   # DATA_BASE_URL – Mock-Daten
    max_steps: int       # MAX_STEPS – höchstens so viele Modellaufrufe pro Lauf


def load_config() -> Config:
    # override=False: Schon gesetzte Umgebungsvariablen haben Vorrang vor .env.
    load_dotenv(ENV_FILE, override=False)

    names = ["OPENAI_BASE_URL", "MODEL", "OPENAI_API_KEY", "DATA_BASE_URL"]
    values = {name: os.environ.get(name, "").strip() for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ConfigError("Konfiguration fehlt: " + ", ".join(missing))

    max_steps = os.environ.get("MAX_STEPS", str(DEFAULT_MAX_STEPS)).strip()
    if not max_steps.isdigit() or int(max_steps) < 1:
        raise ConfigError("MAX_STEPS muss eine positive ganze Zahl sein.")

    return Config(
        base_url=values["OPENAI_BASE_URL"],
        model=values["MODEL"],
        api_key=values["OPENAI_API_KEY"],
        data_base_url=values["DATA_BASE_URL"],
        max_steps=int(max_steps),
    )
