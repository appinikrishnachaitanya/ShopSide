import os
from alembic import context
from sqlalchemy import create_engine
engine=create_engine('sqlite:///'+os.getenv('SHOPSIDE_DB','/tmp/shopside.sqlite3'))
with engine.connect() as connection:
    context.configure(connection=connection)
    with context.begin_transaction(): context.run_migrations()
