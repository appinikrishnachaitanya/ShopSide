"""Cloud Tasks dispatch is deterministic and keeps retries safe."""
from types import SimpleNamespace

from app import merchant_tasks


def test_local_fallback_needs_no_gcp_identity(monkeypatch):
    for name in ('GOOGLE_CLOUD_PROJECT','CLOUD_TASKS_LOCATION','CLOUD_TASKS_QUEUE',
                 'CLOUD_TASKS_TARGET_URL','CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT'):
        monkeypatch.delenv(name,raising=False)
    assert merchant_tasks.enqueue('job-local') is False


def test_immediate_authenticated_dispatch_and_duplicate_delivery(monkeypatch):
    values={'GOOGLE_CLOUD_PROJECT':'demo-project','CLOUD_TASKS_LOCATION':'us-central1',
            'CLOUD_TASKS_QUEUE':'merchant-offers','CLOUD_TASKS_TARGET_URL':'https://backend.example',
            'CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT':'tasks@example.iam.gserviceaccount.com'}
    for key,value in values.items():monkeypatch.setenv(key,value)
    credential=SimpleNamespace(token='access-token',refresh=lambda _request:None)
    monkeypatch.setattr(merchant_tasks.google.auth,'default',lambda **_kwargs:(credential,'demo-project'))
    sent=[]
    def post(url,**kwargs):
        sent.append((url,kwargs))
        return SimpleNamespace(status_code=200 if len(sent)==1 else 409,raise_for_status=lambda:None)
    monkeypatch.setattr(merchant_tasks.httpx,'post',post)
    assert merchant_tasks.enqueue('stable-job') is True
    assert merchant_tasks.enqueue('stable-job') is True
    url,request=sent[0]
    assert url.endswith('/queues/merchant-offers/tasks')
    task=request['json']['task']
    assert task['name'].endswith('/tasks/stable-job')
    assert task['httpRequest']['url']=='https://backend.example/api/internal/merchant-jobs/stable-job/process'
    assert task['httpRequest']['oidcToken']['audience']=='https://backend.example'
    assert task['httpRequest']['oidcToken']['serviceAccountEmail']==values['CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT']


def test_partial_cloud_tasks_configuration_is_rejected(monkeypatch):
    for name in ('GOOGLE_CLOUD_PROJECT','CLOUD_TASKS_LOCATION','CLOUD_TASKS_QUEUE',
                 'CLOUD_TASKS_TARGET_URL','CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT'):
        monkeypatch.delenv(name,raising=False)
    monkeypatch.setenv('CLOUD_TASKS_QUEUE','merchant-offers')
    try:merchant_tasks.configured()
    except RuntimeError as exc:assert 'incomplete' in str(exc)
    else:raise AssertionError('Partial task configuration must fail closed')
