from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re


def _safe_load_dotenv() -> None:
    """잘못된 .env로 인한 파싱 경고/중단을 피한다."""
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
            # 형식이 잘못된 .env면 로딩을 건너뛰고 OS 환경변수를 사용한다.
            return

    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=env_path, override=False, verbose=False)
    except Exception:
        return


_safe_load_dotenv()


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
