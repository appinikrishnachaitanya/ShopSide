"""Exercise the importer with disposable SQLite databases standing in for its destination."""
import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

SCRIPT=Path(__file__).resolve().parents[3]/'scripts/db/import_sqlite_to_postgres.py'
spec=importlib.util.spec_from_file_location('shopside_import_script',SCRIPT)
importer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)

SCHEMA={
    'rooms':'id TEXT PRIMARY KEY, invite TEXT, state TEXT',
    'members':'token TEXT PRIMARY KEY, room TEXT, name TEXT',
    'payments':'id TEXT PRIMARY KEY, room TEXT, state TEXT',
    'inventory':'product TEXT, variant TEXT, stock INTEGER',
    'relocation_policies':'id TEXT PRIMARY KEY, state TEXT',
}

def databases(tmp_path, include_policies=True):
    source=tmp_path/'source.sqlite'; destination=tmp_path/'target.sqlite'
    with sqlite3.connect(source) as db:
        for name,columns in SCHEMA.items():
            if name!='relocation_policies' or include_policies:db.execute(f'CREATE TABLE {name} ({columns})')
        db.execute('INSERT INTO rooms VALUES (?,?,?)',('room','invite','{}'))
        if include_policies:db.execute('INSERT INTO relocation_policies VALUES (?,?)',('policy','{}'))
    engine=create_engine('sqlite:///'+str(destination))
    with engine.begin() as db:
        for name,columns in SCHEMA.items():db.execute(text(f'CREATE TABLE {name} ({columns})'))
    return source,engine

def invoke(monkeypatch,source,engine):
    monkeypatch.setenv('DATABASE_URL','postgresql+psycopg://test')
    monkeypatch.setattr(importer,'database_url',lambda:'postgresql+psycopg://test')
    monkeypatch.setattr(importer,'create_engine',lambda *a,**kw:engine)
    monkeypatch.setattr(sys,'argv',['import_sqlite_to_postgres.py',str(source)])
    importer.main()

@pytest.mark.parametrize('include_policies',[True,False])
def test_import_preserves_policies_and_supports_older_databases(tmp_path,monkeypatch,include_policies):
    source,engine=databases(tmp_path,include_policies)
    invoke(monkeypatch,source,engine)
    with engine.connect() as db:
        assert db.execute(text('SELECT id FROM rooms')).scalar_one()=='room'
        assert db.execute(text('SELECT COUNT(*) FROM relocation_policies')).scalar_one()==int(include_policies)
    with sqlite3.connect(source) as db:assert db.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]==1

def test_import_refuses_nonempty_destination(tmp_path,monkeypatch):
    source,engine=databases(tmp_path)
    with engine.begin() as db:db.execute(text("INSERT INTO members VALUES ('already','there','A')"))
    with pytest.raises(RuntimeError,match='not empty'):invoke(monkeypatch,source,engine)
    with engine.connect() as db:assert db.execute(text('SELECT COUNT(*) FROM rooms')).scalar_one()==0
