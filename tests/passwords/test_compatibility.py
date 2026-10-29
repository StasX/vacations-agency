"""Cross-application contract checks, outside either backend's test suite."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]


def run_backend(application, code, value=''):
    environment = {**os.environ, 'PYTHON_DOTENV_DISABLED': '1', 'APP_ENV': 'production'}
    result = subprocess.run(
        [sys.executable, '-c', 'from utils.security import Security; ' + code],
        cwd=ROOT / application / 'src', env=environment, input=value,
        capture_output=True, text=True, timeout=30, check=True,
    )
    return result.stdout.strip()


@pytest.mark.parametrize('producer,consumer', [('Flask', 'Django'), ('Django', 'Flask')])
def test_password_hashes_work_across_backends(producer, consumer):
    stored_hash = run_backend(producer, "print(Security.hash('Password123!'))")
    result = run_backend(consumer,
        "import sys; stored = sys.stdin.read(); "
        "assert Security.verify('Password123!', stored); "
        "assert not Security.verify('WrongPassword!', stored)", stored_hash)
    assert result == ''
