"""Migration checks for Phase 58 drawdown settings."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_phase58_migration_adds_modes_and_preserves_legacy_total_mode(tmp_path):
    database_path = tmp_path / "phase58.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('54a1b2c3d4e5')"))
        connection.execute(text("CREATE TABLE prop_stages (id INTEGER PRIMARY KEY, dd_mode VARCHAR(20) NOT NULL DEFAULT 'static', dd_basis VARCHAR(20) NOT NULL DEFAULT 'balance')"))
        connection.execute(text("INSERT INTO prop_stages (dd_mode, dd_basis) VALUES ('trailing', 'equity')"))
        connection.execute(text("CREATE TABLE trades (id INTEGER PRIMARY KEY, sl FLOAT, initial_sl FLOAT, raw_data TEXT)"))

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "58a1b2c3d4e5")

    with engine.connect() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("prop_stages")}
        assert {"dd_basis", "daily_dd_mode", "total_dd_mode"} <= columns
        row = connection.execute(text("SELECT dd_basis, daily_dd_mode, total_dd_mode FROM prop_stages")).one()
        assert tuple(row) == ("equity", "static", "trailing")
    engine.dispose()