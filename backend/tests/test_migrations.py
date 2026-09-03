from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import sessionmaker

from app import seed
from app.core.config import settings
from app.core.security import verify_password
from app.db.base import Base
from app.models.entities import User


@pytest.fixture(autouse=True)
def database():
    # Migration tests use only their own temporary database, not test.db.
    yield


@pytest.fixture
def migration_db(tmp_path, monkeypatch):
    backend = Path(__file__).resolve().parents[1]
    url = 'sqlite:///' + (tmp_path / 'migration.db').as_posix()
    monkeypatch.setattr(settings, 'database_url', url)
    config = Config(str(backend / 'alembic.ini'))
    config.set_main_option('script_location', str(backend / 'alembic'))
    engine = sa.create_engine(url)
    yield config, engine
    engine.dispose()


def insert_business_data(engine):
    with engine.begin() as db:
        db.execute(sa.text("INSERT INTO users (id, username, full_name, email, password_hash, role, is_active, created_at, updated_at) VALUES (1, 'admin', 'Existing Admin', 'admin@example.com', 'preserve-this-hash', 'ADMIN', 1, '2026-09-01', '2026-09-01')"))
        db.execute(sa.text("INSERT INTO user_stories (id, code, title, status, priority, progress_percent, created_by, created_at, updated_at) VALUES (1, 'US-KEEP', 'Keep story', 'TODO', 'MEDIUM', 0, 1, '2026-09-01', '2026-09-01')"))
        flag = ', is_reopened' if 'is_reopened' in {c['name'] for c in sa.inspect(db).get_columns('daily_reports')} else ''
        value = ', 1' if flag else ''
        db.execute(sa.text(f"INSERT INTO daily_reports (id, user_id, report_date, status, general_note, created_at, updated_at{flag}) VALUES (1, 1, '2026-09-01', 'DRAFT', 'Keep daily', '2026-09-01', '2026-09-01'{value})"))
        db.execute(sa.text("INSERT INTO daily_report_items (id, daily_report_id, user_story_id, task_title, has_issue, created_at, updated_at) VALUES (1, 1, 1, 'Keep task', 0, '2026-09-01', '2026-09-01')"))
        db.execute(sa.text("INSERT INTO weekly_reports (id, week_start, week_end, generated_by, generated_at, snapshot_data, status) VALUES (1, '2026-09-01', '2026-09-02', 1, '2026-09-02', :snapshot, 'FINALIZED')"), {'snapshot': '{"unchanged":true}'})
        if sa.inspect(db).has_table('daily_report_reopen_audits'):
            db.execute(sa.text("INSERT INTO daily_report_reopen_audits (id, daily_report_id, reopened_by, reason, reopened_at) VALUES (1, 1, 1, 'Keep audit', '2026-09-02')"))


def business_snapshot(engine):
    names = ('users', 'user_stories', 'daily_reports', 'daily_report_items', 'weekly_reports', 'daily_report_reopen_audits')
    with engine.connect() as db:
        result = {}
        for name in names:
            if sa.inspect(db).has_table(name):
                rows = db.execute(sa.text(f'SELECT * FROM {name} ORDER BY id')).mappings()
                result[name] = [{k: v for k, v in row.items() if k != 'is_reopened'} for row in rows]
        return result


def assert_head(engine):
    with engine.connect() as db:
        assert db.scalar(sa.text('SELECT version_num FROM alembic_version')) == '0002_daily_reopen_audit'
        assert list(db.execute(sa.text('PRAGMA foreign_key_check'))) == []
    assert 'is_reopened' in {c['name'] for c in sa.inspect(engine).get_columns('daily_reports')}
    assert sa.inspect(engine).has_table('daily_report_reopen_audits')


def test_fresh_migrations_and_admin_only_seed(migration_db, monkeypatch):
    config, engine = migration_db
    command.upgrade(config, '0001_initial')
    assert 'is_reopened' not in {c['name'] for c in sa.inspect(engine).get_columns('daily_reports')}
    assert not sa.inspect(engine).has_table('daily_report_reopen_audits')
    command.upgrade(config, 'head')
    assert_head(engine)
    # Compare column names/nullability/types against the current application.
    for table in Base.metadata.sorted_tables:
        columns = {c['name']: c for c in sa.inspect(engine).get_columns(table.name)}
        assert set(columns) == set(table.c.keys())
        for column in table.columns:
            assert columns[column.name]['nullable'] == column.nullable
            assert str(columns[column.name]['type']) == str(column.type.compile(dialect=engine.dialect))
    monkeypatch.setattr(seed, 'SessionLocal', sessionmaker(bind=engine))
    monkeypatch.setattr(settings, 'admin_initial_password', 'MigrationTest123!')
    seed.run()
    seed.run()
    with sessionmaker(bind=engine)() as db:
        admin = db.scalars(sa.select(User)).one()
        assert admin.username == 'admin'
        assert verify_password('MigrationTest123!', admin.password_hash)
        for table in Base.metadata.sorted_tables:
            if table.name != 'users':
                assert db.scalar(sa.select(sa.func.count()).select_from(table)) == 0


@pytest.mark.parametrize('state', ['legacy', 'column_only', 'broken_initial', 'broken_unstamped', 'missing_indexes'])
def test_upgrade_preserves_data_and_recovers_partial_schema(migration_db, state):
    config, engine = migration_db
    if state in ('legacy', 'column_only'):
        command.upgrade(config, '0001_initial')
        if state == 'column_only':
            with engine.begin() as db:
                db.execute(sa.text('ALTER TABLE daily_reports ADD COLUMN is_reopened BOOLEAN NOT NULL DEFAULT 0'))
    else:
        # Reproduce the old 0001: all CURRENT model tables already exist.
        Base.metadata.create_all(engine)
        if state != 'broken_unstamped':
            command.stamp(config, '0001_initial')
        if state == 'missing_indexes':
            for index in list(Base.metadata.tables['daily_report_reopen_audits'].indexes):
                index.drop(engine)
    insert_business_data(engine)
    before = business_snapshot(engine)
    command.upgrade(config, 'head')
    assert_head(engine)
    after = business_snapshot(engine)
    assert all(after[name] == rows for name, rows in before.items())
    with engine.connect() as db:
        assert db.scalar(sa.text('SELECT is_reopened FROM daily_reports WHERE id=1')) == (0 if state == 'legacy' else 1)
    indexes = sa.inspect(engine).get_indexes('daily_report_reopen_audits')
    assert sorted(tuple(index['column_names']) for index in indexes) == [('daily_report_id',), ('reopened_at',), ('reopened_by',)]
    command.upgrade(config, 'head')
    assert business_snapshot(engine) == after


def test_downgrade_and_upgrade_on_temporary_database(migration_db):
    config, engine = migration_db
    command.upgrade(config, 'head')
    command.downgrade(config, '0001_initial')
    assert 'is_reopened' not in {c['name'] for c in sa.inspect(engine).get_columns('daily_reports')}
    command.upgrade(config, 'head')
    assert_head(engine)
