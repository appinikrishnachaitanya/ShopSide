#!/usr/bin/env python3
"""Copy ShopSide data from SQLite to an empty, migrated PostgreSQL database.

Stop all app instances and back up both databases first. DATABASE_URL selects the
PostgreSQL destination; this script never prints it or changes the SQLite source.
"""
import argparse
import os
import sqlite3
from pathlib import Path
from sqlalchemy import create_engine, text
from app.database import database_url

TABLES={
    'rooms':('id','invite','state'),
    'members':('token','room','name'),
    'payments':('id','room','state'),
    'inventory':('product','variant','stock'),
}
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',help='Path to existing SQLite database')
    args=parser.parse_args()
    if not os.environ.get('DATABASE_URL') or not database_url().startswith('postgresql+psycopg://'):
        parser.error('DATABASE_URL must name the destination PostgreSQL database')
    source_path=Path(args.source).resolve(strict=True)
    source=sqlite3.connect(source_path.as_uri()+'?mode=ro',uri=True)
    engine=create_engine(database_url(),pool_pre_ping=True)
    try:
        source.execute('BEGIN')
        with engine.begin() as dest:
            for table in TABLES:
                if dest.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar_one():
                    raise RuntimeError(f'Destination table {table} is not empty; no data was imported')
            for table,columns in TABLES.items():
                names=','.join(columns)
                rows=source.execute(f'SELECT {names} FROM {table}').fetchall()
                if rows:
                    params=','.join(':'+name for name in columns)
                    dest.execute(text(f'INSERT INTO {table} ({names}) VALUES ({params})'),[dict(zip(columns,row)) for row in rows])
                print(f'{table}: {len(rows)} rows copied')
    finally:
        source.close()
        engine.dispose()
if __name__=='__main__': main()
