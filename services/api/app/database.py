"""Database settings and DB-API compatibility for SQLite and Cloud SQL Postgres."""
import os
import threading
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

def database_url():
    value=os.getenv('DATABASE_URL')
    if not value:
        if os.getenv('K_SERVICE') or os.getenv('REQUIRE_POSTGRES','').lower()=='true':
            raise ValueError('DATABASE_URL for PostgreSQL is required in production')
        return 'sqlite:///'+os.getenv('SHOPSIDE_DB','/tmp/shopside.sqlite3')
    if value.startswith('postgres://'): value='postgresql+psycopg://'+value[len('postgres://'):]
    elif value.startswith('postgresql://'): value='postgresql+psycopg://'+value[len('postgresql://'):]
    url=make_url(value)
    if (os.getenv('K_SERVICE') or os.getenv('REQUIRE_POSTGRES','').lower()=='true') and url.get_backend_name()!='postgresql':
        raise ValueError('PostgreSQL is required in production')
    if url.get_backend_name() not in ('postgresql','sqlite'):
        raise ValueError('DATABASE_URL must use PostgreSQL or SQLite')
    return value

def make_engine():
    url=database_url()
    if make_url(url).get_backend_name()=='sqlite':
        return create_engine(url,connect_args={'check_same_thread':False,'timeout':5},pool_pre_ping=True)
    return create_engine(url,pool_pre_ping=True,pool_recycle=1800)

class Database:
    """Adapter preserving the existing parameterized statements across both drivers.

    This service currently uses one worker and one process-local serialized connection;
    database-backed multi-instance coordination is not provided.
    """
    def __init__(self,engine):
        self.engine=engine
        self.guard=threading.RLock()
        self.postgres=engine.dialect.name=='postgresql'
        self.connection=None
        self.raw=None
        self._connect()
    def _connect(self):
        self.connection=self.engine.raw_connection()
        self.raw=self.connection.driver_connection
        if self.postgres:
            self.raw.autocommit=True
        else:
            self.raw.execute('PRAGMA journal_mode=WAL')
            self.raw.execute('PRAGMA busy_timeout=5000')
    def _discard(self):
        if self.connection:
            self.connection.invalidate()
            self.connection.close()
        self.connection=None
        self.raw=None
    def execute(self,sql,params=()):
        with self.guard:
            if self.connection is None or (self.postgres and self.raw.closed):
                if self.connection:self._discard()
                self._connect()
            if self.postgres:sql=sql.replace('?', '%s')
            try:return self.raw.execute(sql,params)
            except Exception:
                try:self.raw.rollback()
                except Exception:self._discard()
                raise
    def begin(self):
        with self.guard:self.execute('BEGIN')
    def commit(self):
        with self.guard:
            try:self.raw.commit()
            except Exception:
                self._discard()
                raise
    def rollback(self):
        with self.guard:
            if self.raw:
                try:self.raw.rollback()
                except Exception:self._discard()
