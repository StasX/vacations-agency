from pathlib import Path
import shutil
import subprocess
import pytest


def test_javascript_ui_suite():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the JavaScript UI tests")
    script = Path(__file__).parent / "js/ui.test.cjs"
    result = subprocess.run(
        [node, "--test", str(script)], capture_output=True, text=True,
        encoding="utf-8", timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
