"""Dispatch durable merchant jobs through Cloud Tasks when configured."""
import os
from urllib.parse import quote

import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import httpx


def configured():
    names=('GOOGLE_CLOUD_PROJECT','CLOUD_TASKS_LOCATION','CLOUD_TASKS_QUEUE',
           'CLOUD_TASKS_TARGET_URL','CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT')
    present=[bool(os.getenv(name)) for name in names]
    if any(present) and not all(present):
        raise RuntimeError('Cloud Tasks configuration is incomplete')
    return all(present)


def enqueue(job_id,path=None):
    """A failed enqueue leaves the durable pending job recoverable for retry."""
    if not configured():return False
    project=os.environ['GOOGLE_CLOUD_PROJECT']
    location=os.environ['CLOUD_TASKS_LOCATION']
    queue=os.environ['CLOUD_TASKS_QUEUE']
    base=f'projects/{project}/locations/{location}/queues/{queue}'
    target=os.environ['CLOUD_TASKS_TARGET_URL'].rstrip('/')
    audience=os.getenv('CLOUD_TASKS_OIDC_AUDIENCE',target)
    credentials,_=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    credentials.refresh(Request())
    task_name=quote(job_id,safe='')
    if path is None:path=f'/api/internal/merchant-jobs/{task_name}/process'
    body={'task':{'name':f'{base}/tasks/{task_name}',
        'httpRequest':{'httpMethod':'POST','url':f'{target}{path}',
            'headers':{'Content-Type':'application/json'},
            'oidcToken':{'serviceAccountEmail':os.environ['CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT'],
                         'audience':audience}}}}
    response=httpx.post(f'https://cloudtasks.googleapis.com/v2/{base}/tasks',
        headers={'Authorization':f'Bearer {credentials.token}'},json=body,timeout=10)
    if response.status_code==409:return True
    response.raise_for_status()
    return True


def verify(request):
    if not configured():return False
    bearer=request.headers.get('authorization','')
    if not bearer.startswith('Bearer '):return False
    target=os.environ['CLOUD_TASKS_TARGET_URL'].rstrip('/')
    audience=os.getenv('CLOUD_TASKS_OIDC_AUDIENCE',target)
    try:
        claims=id_token.verify_oauth2_token(bearer[7:],Request(),audience=audience)
    except (ValueError,TypeError):return False
    return claims.get('email')==os.environ['CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT'] and claims.get('email_verified') is True
