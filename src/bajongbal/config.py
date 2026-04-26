from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re


_REQUIRED_KEYS = ('KIS_APP_KEY', 'KIS_APP_SECRET', 'KIS_BASE_URL', 'DART_API_KEY')
_ENV_META: dict = {
    'cwd': str(Path.cwd()),
    'env_candidate_paths': [],
    'selected_env_file': None,
    'env_file_exists': False,
    'env_file_loaded': False,
    'invalid_env_line_count': 0,
    'invalid_env_line_numbers': [],
}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    return v if v else None


def _candidate_env_paths() -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()

    env_file = _clean(os.getenv('BAJONGBAL_ENV_FILE'))
    if env_file:
        p = Path(env_file).expanduser()
        p = p if p.is_absolute() else (Path.cwd() / p)
        p = p.resolve()
        out.append(p)
        seen.add(str(p))

    cwd_env = (Path.cwd() / '.env').resolve()
    if str(cwd_env) not in seen:
        out.append(cwd_env)
        seen.add(str(cwd_env))

    config_file = Path(__file__).resolve()
    for parent in config_file.parents:
        p = (parent / '.env').resolve()
        if str(p) not in seen:
            out.append(p)
            seen.add(str(p))

    repo_env = (Path(__file__).resolve().parents[2] / '.env').resolve()
    if str(repo_env) not in seen:
        out.append(repo_env)

    return out


def _validate_env_lines(path: Path) -> tuple[int, list[int]]:
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except Exception:
        return 0, []

    invalid: list[int] = []
    for idx, line in enumerate(lines, start=1):
        raw = line.strip()
        if not raw or raw.startswith('#'):
            continue
        if raw.startswith('export '):
            raw = raw[len('export '):].strip()
        if '=' not in raw:
            invalid.append(idx)
            continue
        key, _ = raw.split('=', 1)
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*\s*$', key.strip()):
            invalid.append(idx)
            continue
    return len(invalid), invalid


def _safe_load_dotenv() -> None:
    candidates = _candidate_env_paths()
    _ENV_META['cwd'] = str(Path.cwd())
    _ENV_META['env_candidate_paths'] = [str(p) for p in candidates]

    selected = next((p for p in candidates if p.exists()), None)
    _ENV_META['selected_env_file'] = str(selected) if selected else None
    _ENV_META['env_file_exists'] = bool(selected and selected.exists())

    if not selected:
        return

    invalid_count, invalid_lines = _validate_env_lines(selected)
    _ENV_META['invalid_env_line_count'] = invalid_count
    _ENV_META['invalid_env_line_numbers'] = invalid_lines

    try:
        from dotenv import dotenv_values

        parsed = dotenv_values(selected)
        for key, value in parsed.items():
            if not key:
                continue
            cleaned = _clean(value)
            if cleaned is None:
                continue
            current = _clean(os.getenv(key))
            if current is None:
                os.environ[key] = cleaned
        _ENV_META['env_file_loaded'] = True
    except Exception:
        _ENV_META['env_file_loaded'] = False


def env_diagnostics() -> dict:
    key_flags = {k: ('Y' if bool(_clean(os.getenv(k))) else 'N') for k in _REQUIRED_KEYS}
    return {
        **_ENV_META,
        'env_file_path': _ENV_META.get('selected_env_file'),
        **key_flags,
    }


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
        return bool(_clean(os.getenv('KIS_APP_KEY')))

    @property
    def has_kis_app_secret(self) -> bool:
        return bool(_clean(os.getenv('KIS_APP_SECRET')))

    @property
    def has_kis_base_url(self) -> bool:
        return bool(_clean(os.getenv('KIS_BASE_URL')))

    @property
    def has_dart_api_key(self) -> bool:
        return bool(_clean(os.getenv('DART_API_KEY')))


settings = Settings()
