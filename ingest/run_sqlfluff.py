"""Run SQLFluff with the same local dbt credentials, without sourcing shell code."""
import os
import subprocess
import sys
from pathlib import Path

from ingest.db import ROOT, connection_settings


def main():
    settings = connection_settings()
    env = os.environ.copy()
    env["DBT_ENV_SECRET_PG_PASSWORD"] = settings["password"]
    env["DBT_SEND_ANONYMOUS_USAGE_STATS"] = "false"
    return subprocess.run(
        [str(Path(sys.executable).parent / "sqlfluff"), *sys.argv[1:]],
        cwd=ROOT,
        env=env,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
