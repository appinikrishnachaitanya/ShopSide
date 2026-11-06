import json, os, secrets, sqlite3, threading
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

app = FastAPI(title='ShopSide')
lock = threading.RLock()
db = sqlite3.connect(os.getenv('SHOPSIDE_DB', '/tmp/shopside.sqlite3'), check_same_thread=False)
db.execute('PRAGMA journal_mode=WAL')
db.execute('PRAGMA busy_timeout=5000')
db.execute('CREATE TABLE IF NOT EXISTS rooms(id TEXT PRIMARY KEY, invite TEXT UNIQUE, state TEXT)')
db.execute('CREATE TABLE IF NOT EXISTS members(token TEXT PRIMARY KEY, room TEXT, name TEXT)')
catalog = [dict(id=str(i), name=n, price=p, currency='USD', description='Fictional sample headphones · demo inventory') for i,(n,p) in enumerate([('Sunday Studio',8900),('Everyday Air',6900),('Quiet Hours',9900),('City Rhythm',7900),('Soft Signal',5900),('Open Road',9500),('Little Escape',4900),('Evening Edit',8500)])]
class Entry(BaseModel):
    name: str = Field(min_length=1,max_length=40)
    title: str = Field(default='Headphones for my commute',max_length=100)
class Command(BaseModel):
    command_id: str = Field(min_length=1,max_length=100)
    revision: int
    kind: str
    value: str = Field(max_length=1000)
def load(r):
    row=db.execute('SELECT state FROM rooms WHERE id=?',(r,)).fetchone()
    if not row: raise HTTPException(404,'Room not found')
    return json.loads(row[0])
def save(r,s):
    db.execute('UPDATE rooms SET state=? WHERE id=?',(json.dumps(s),r)); db.commit()
def auth(r,request):
    row=db.execute('SELECT name FROM members WHERE room=? AND token=?',(r,request.cookies.get('membership',''))).fetchone()
    if not row: raise HTTPException(403,'Membership required')
    return row[0]
def member(response,r,name):
    token=secrets.token_urlsafe(32)
    db.execute('INSERT INTO members VALUES(?,?,?)',(token,r,name)); db.commit()
    response.set_cookie('membership',token,httponly=True,samesite='lax',max_age=604800)
@app.get('/api/catalog')
def products(): return catalog
@app.post('/api/rooms')
def create(body:Entry,response:Response):
    with lock:
        r=secrets.token_urlsafe(18); invite=secrets.token_urlsafe(32)
        s=dict(id=r,title=body.title,revision=0,people=[body.name],payer=body.name,focus='0',shortlist=[],reactions={},messages=[],commands=[])
        db.execute('INSERT INTO rooms VALUES(?,?,?)',(r,invite,json.dumps(s)))
        member(response,r,body.name)
        return dict(room=s,invite=invite)
@app.post('/api/join/{invite}')
def join(invite:str,body:Entry,response:Response):
    with lock:
        row=db.execute('SELECT id FROM rooms WHERE invite=?',(invite,)).fetchone()
        if not row: raise HTTPException(404,'Invalid invitation')
        r=row[0]; s=load(r)
        if len(s['people'])>=2: raise HTTPException(409,'Room is full')
        if body.name in s['people']: raise HTTPException(409,'Choose a different name')
        s['people'].append(body.name); s['revision']+=1; save(r,s); member(response,r,body.name)
        return s
@app.get('/api/rooms/{r}')
def room(r:str,request:Request):
    with lock:
        auth(r,request); s=load(r); return {k:v for k,v in s.items() if k!='commands'}
@app.post('/api/rooms/{r}/commands')
def command(r:str,body:Command,request:Request):
    with lock:
        actor=auth(r,request); s=load(r)
        if body.command_id in s['commands']: return {'ok':True}
        if body.revision!=s['revision']: raise HTTPException(409,'Room changed; refresh and retry')
        if body.kind in ['focus','shortlist','reaction'] and body.value not in [p['id'] for p in catalog]: raise HTTPException(422,'Unknown product')
        if body.kind=='focus': s['focus']=body.value; s['spotlight_by']=actor
        elif body.kind=='shortlist':
            if body.value in s['shortlist']: s['shortlist'].remove(body.value)
            else: s['shortlist'].append(body.value)
        elif body.kind=='reaction':
            people=s['reactions'].setdefault(body.value,[])
            if actor in people: people.remove(actor)
            else: people.append(actor)
        elif body.kind=='chat': s['messages'].append(dict(actor=actor,text=body.value))
        else: raise HTTPException(422,'Unknown command')
        s['revision']+=1; s['commands'].append(body.command_id); save(r,s)
        return {'ok':True}
