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

@pytest.fixture
def mock_bundle_runner(monkeypatch):
    """Exercise registered ADK tools with deterministic calls, without a model request."""
    from types import SimpleNamespace
    import app.smart_bundle_agent as module
    class Sessions:
        async def create_session(self,**kwargs):return SimpleNamespace(id='session')
    class Runner:
        def __init__(self,agent,app_name):self.agent=agent;self.session_service=Sessions()
        async def run_async(self,**kwargs):
            import json
            assert kwargs['run_config'].max_llm_calls==6
            data=json.loads(kwargs['new_message'].parts[0].text)
            for index,category in enumerate(data['requirements']):
                result=await self.agent.tools[0](index,[category])
                assert 'products' in result
            result=await self.agent.tools[1]()
            assert 'count' in result
            yield SimpleNamespace()
    class Client:
        def close(self):pass
    monkeypatch.setattr(module,'InMemoryRunner',Runner)
    monkeypatch.setattr(module,'Gemini',lambda **kwargs:'mock-model')
    monkeypatch.setattr(module,'configured_client',lambda:Client())
    monkeypatch.setenv('GEMINI_MODEL','mock-model')
