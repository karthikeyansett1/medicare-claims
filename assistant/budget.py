"""Persistent atomic server-wide reservations; failed calls still consume budget."""
import os
from pathlib import Path
import sqlite3
import time
from ingest.db import ROOT

class BudgetError(RuntimeError):
    pass


def reserve(input_bound, output_bound, path=None):
    path = Path(path or ROOT / 'assistant/logs/budget.sqlite3')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with sqlite3.connect(path, timeout=10) as db:
        db.execute('CREATE TABLE IF NOT EXISTS calls (created REAL, tokens INTEGER)')
        db.execute('BEGIN IMMEDIATE')
        now = time.time()
        minute = db.execute('SELECT COUNT(*) FROM calls WHERE created>?', (now-60,)).fetchone()[0]
        day_count, day_tokens = db.execute('SELECT COUNT(*), COALESCE(SUM(tokens),0) FROM calls WHERE created>?',(now-86400,)).fetchone()
        if minute >= int(os.getenv('ASSISTANT_CALLS_PER_MINUTE','6')):
            raise BudgetError('Server minute request limit reached. Try later.')
        if day_count >= int(os.getenv('ASSISTANT_CALLS_PER_DAY','60')) or day_tokens+input_bound+output_bound > int(os.getenv('ASSISTANT_TOKEN_BUDGET_PER_DAY','1000000')):
            raise BudgetError('Server daily request/token budget reached.')
        db.execute('INSERT INTO calls VALUES (?,?)',(now,input_bound+output_bound))
    path.chmod(0o600)
