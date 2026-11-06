#!/usr/bin/env python3
"""Exercise one production build with two different runtime backend URLs."""
import json
import os
import socket
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class Backend(BaseHTTPRequestHandler):
    def do_GET(self):
        data=json.dumps({'backend':self.server.label,'path':self.path,'cookie':self.headers.get('Cookie')}).encode()
        self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(data)
    def log_message(self,*args): pass

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0)); return s.getsockname()[1]

def main():
    backends=[]; processes=[]
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        for label in ['one','two']:
            server=ThreadingHTTPServer(('127.0.0.1',0),Backend);server.label=label
            threading.Thread(target=server.serve_forever,daemon=True).start();backends.append(server)
            port=free_port()
            env={**os.environ,'NODE_ENV':'production','PORT':str(port),'BACKEND_URL':f'http://127.0.0.1:{server.server_port}'}
            env.pop('BACKEND_ID_TOKEN_AUDIENCE',None)
            proc=subprocess.Popen(['node','server.cjs'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);processes.append(proc)
            endpoint=f'http://127.0.0.1:{port}/api/probe?value=test'
            deadline=time.monotonic()+25
            while True:
                try:
                    request=urllib.request.Request(endpoint,headers={'Cookie':'membership=test-cookie'})
                    with opener.open(request,timeout=2) as response: result=json.load(response)
                    break
                except OSError:
                    if proc.poll() is not None or time.monotonic()>deadline:raise
                    time.sleep(.2)
            assert result=={'backend':label,'path':'/api/probe?value=test','cookie':'membership=test-cookie'},result
        print('PASS: same build routed to both runtime backends and forwarded cookies/query')
    finally:
        for proc in processes:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
        for server in backends:server.shutdown();server.server_close()
if __name__=='__main__':main()
