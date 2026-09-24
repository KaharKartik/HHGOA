import json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
import app.integrations.tigergraph.adapter as module
from app.integrations.tigergraph import TigerGraphAdapter

class Response:
 def __enter__(self): return self
 def __exit__(self,*_): return False
 def read(self): return b'{"error": false, "results": {}}'
def test_schema_uses_gsql_v1_and_secret_header(monkeypatch):
 captured={}
 def open_mock(request,timeout): captured['url']=request.full_url; captured['auth']=request.get_header('Authorization'); return Response()
 monkeypatch.setattr(module,'urlopen',open_mock)
 result=TigerGraphAdapter('https://workspace.tgcloud.io','HHGOA_FRAUD',secret='test-secret').get_schema()
 assert '/gsql/v1/schema/graphs/HHGOA_FRAUD' in captured['url']
 assert captured['auth']=='GSQL-Secret test-secret'
 assert result['error'] is False
