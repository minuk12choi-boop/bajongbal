from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    def load_dotenv():
        return False


load_dotenv()


@dataclass(slots=True)
class Settings:
    data_dir: Path = Path('data')
    output_dir: Path = Path('outputs')
    db_path: Path = Path('data/bajongbal.sqlite3')
    kis_app_key: str | None = os.getenv('KIS_APP_KEY')
    kis_app_secret: str | None = os.getenv('KIS_APP_SECRET')
    kis_base_url: str = os.getenv('KIS_BASE_URL', 'https://openapi.koreainvestment.com:9443')
    dart_api_key: str | None = os.getenv('DART_API_KEY')


settings = Settings()
