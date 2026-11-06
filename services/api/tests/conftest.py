"""Isolate integration tests from deployment databases and per-process limits."""
import os
import tempfile
import pytest
os.environ['SHOPSIDE_DB']=tempfile.mktemp(prefix='shopside-test-',suffix='.sqlite3')
if os.getenv('SHOPSIDE_TEST_DATABASE_URL'):
    os.environ['DATABASE_URL']=os.environ['SHOPSIDE_TEST_DATABASE_URL']
else:
    os.environ.pop('DATABASE_URL',None)

@pytest.fixture(autouse=True)
def reset_test_rate_limits():
    from app.main import limits
    limits.clear()
    yield
    limits.clear()
