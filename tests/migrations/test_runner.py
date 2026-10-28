"""Migration history policy, independent of a running database."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('migration_runner', Path(__file__).resolve().parents[2] / 'MySQL/migrate.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_migration_catalog_is_nonempty_and_versioned():
    migrations = runner.discover()
    assert '0001' in migrations
    assert len(migrations['0001'][1]) == 64


@pytest.mark.parametrize('case', ['changed', 'missing', 'incomplete', 'out-of-order', 'invalid-retry'])
def test_unsafe_history_is_rejected(tmp_path, case):
    first = tmp_path / '0001__first.py'
    second = tmp_path / '0002__second.py'
    first.write_text('def upgrade(connection): pass\n')
    second.write_text('def upgrade(connection): pass\n')
    migrations = runner.discover(tmp_path)
    recorded = {'0001': (first.name, migrations['0001'][1], 'applied')}
    retry = None
    if case == 'changed':
        first.write_text('# changed\ndef upgrade(connection): pass\n')
        migrations = runner.discover(tmp_path)
    elif case == 'missing':
        migrations.pop('0001')
    elif case == 'incomplete':
        recorded['0001'] = (first.name, migrations['0001'][1], 'running')
    elif case == 'out-of-order':
        recorded = {'0002': (second.name, migrations['0002'][1], 'applied')}
    else:
        retry = '0001'
    with pytest.raises(RuntimeError):
        runner.validate(migrations, recorded, retry)


def test_duplicate_version_is_rejected(tmp_path):
    (tmp_path / '0001__first.py').write_text('')
    (tmp_path / '0001__duplicate.py').write_text('')
    with pytest.raises(RuntimeError, match='Duplicate'):
        runner.discover(tmp_path)
