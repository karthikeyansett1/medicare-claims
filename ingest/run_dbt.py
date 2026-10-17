"""Run project dbt with .env loaded as data, never shell source code."""
import os
import subprocess
import sys
from pathlib import Path
from ingest.db import ROOT, connection_settings


def main():
    settings = connection_settings()
    if any(arg in {'build', 'run'} for arg in sys.argv[1:]):
        from assistant.setup_role import setup_role
        setup_role()
    env = os.environ.copy()
    env['DBT_ENV_SECRET_PG_PASSWORD'] = settings['password']
    env['DBT_SEND_ANONYMOUS_USAGE_STATS'] = 'false'
    command = [str(Path(sys.executable).parent / 'dbt'), *sys.argv[1:],
               '--project-dir', str(ROOT / 'dbt_project'),
               '--profiles-dir', str(ROOT / 'dbt_project')]
    return subprocess.run(command, env=env, cwd=ROOT).returncode


if __name__ == '__main__':
    raise SystemExit(main())
