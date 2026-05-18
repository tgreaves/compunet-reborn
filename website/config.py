import os

_ENV_FILE = os.environ.get('ENV_FILE', '/app/.env')


def _load_env_file():
    """Load .env file into os.environ if it exists."""
    if os.path.exists(_ENV_FILE):
        with open(_ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())


_load_env_file()


def get(key, default=''):
    return os.environ.get(key, default)
