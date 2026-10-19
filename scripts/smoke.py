import json
import sys
from urllib.request import Request, urlopen
base = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://localhost:8080'
def call(path, method='GET', data=None):
    req = Request(base+path, data=json.dumps(data).encode() if data is not None else None,
                  headers={'Content-Type':'application/json'}, method=method)
    with urlopen(req, timeout=15) as response:
        raw = response.read()
        return json.loads(raw) if raw else None
assert call('/api/readyz')['status'] == 'ready'
task = call('/api/tasks', 'POST', {'title':'Deployment smoke test'})
try:
    assert any(t['id'] == task['id'] for t in call('/api/tasks'))
    call('/api/tasks/'+str(task['id']), 'PATCH', {'done':True})
    assert next(t for t in call('/api/tasks') if t['id']==task['id'])['done']
finally:
    call('/api/tasks/'+str(task['id']), 'DELETE')
print('PASS: readiness, persistence, update, delete')
