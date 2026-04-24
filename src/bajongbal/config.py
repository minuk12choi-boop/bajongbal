from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re


def _safe_load_dotenv() -> None:
    env_path = Path('.env')
    if not env_path.exists():
        return
    try:
        lines = env_path.read_text(encoding='utf-8').splitlines()
    except Exception:
        return

    pattern = re.compile(r'^\s*[A-Za-z_][A-Za-z0-9_]*\s*=')
    for line in lines:
        raw = line.strip()
        if not raw or raw.startswith('#'):
            continue
        if not pattern.match(raw):
            return

    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=env_path, override=False, verbose=False)
    except Exception:
        return


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    return v if v else None


_safe_load_dotenv()


@dataclass(slots=True)
class Settings:
    data_dir: Path = Path('data')
    output_dir: Path = Path('outputs')
    db_path: Path = Path('data/bajongbal.sqlite3')
    kis_app_key: str | None = _clean(os.getenv('KIS_APP_KEY'))
    kis_app_secret: str | None = _clean(os.getenv('KIS_APP_SECRET'))
    kis_base_url: str = _clean(os.getenv('KIS_BASE_URL')) or ''
    dart_api_key: str | None = _clean(os.getenv('DART_API_KEY'))

    @property
    def has_kis_app_key(self) -> bool:
        return bool(self.kis_app_key)

    @property
    def has_kis_app_secret(self) -> bool:
        return bool(self.kis_app_secret)

    @property
    def has_kis_base_url(self) -> bool:
        return bool(self.kis_base_url)

    @property
    def has_dart_api_key(self) -> bool:
        return bool(self.dart_api_key)


settings = Settings()
