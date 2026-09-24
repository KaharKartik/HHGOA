"""Typed boundary for GSQL query endpoints; suitable for future MCP tool exposure."""
from __future__ import annotations
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .models import QueryResponse, WriteCaseRequest
class TigerGraphError(RuntimeError): pass
class TigerGraphAdapter:
    def __init__(self, host:str, graph_name:str, token:str|None=None, secret:str|None=None, timeout_s:float=15): self.host=host.rstrip('/'); self.graph_name=graph_name; self.token=token; self.secret=secret; self.timeout_s=timeout_s
    @classmethod
    def from_environment(cls, env_file: str | Path = '.env') -> 'TigerGraphAdapter':
        """Read Savanna configuration without logging the database secret."""
        values=dict(os.environ)
        path=Path(env_file)
        if path.is_file():
            for line in path.read_text(encoding='utf-8').splitlines():
                if '=' in line and not line.lstrip().startswith('#'):
                    key,value=line.split('=',1); values.setdefault(key.strip(),value.strip().strip('"').strip("'"))
        missing=[key for key in ('TG_HOST','TG_GRAPH_NAME') if not values.get(key)]
        if missing: raise TigerGraphError('missing configuration: '+', '.join(missing))
        if not values.get('TG_SECRET') and not values.get('TG_API_TOKEN'):
            raise TigerGraphError('missing configuration: TG_SECRET or TG_API_TOKEN')
        return cls(values['TG_HOST'],values['TG_GRAPH_NAME'],token=values.get('TG_API_TOKEN'),secret=values.get('TG_SECRET'))
    def _restpp_url(self, path: str) -> str:
        base=self.host if self.host.endswith('/restpp') else f'{self.host}/restpp'
        return f'{base}/{path.lstrip("/")}'
    def _token(self) -> str | None:
        # Savanna database secrets are the preferred credential. A supplied
        # API token remains a compatibility fallback for existing deployments.
        if not self.secret:return self.token
        if self.token:return self.token
        request=Request(f'{self._restpp_url("requesttoken")}?{urlencode({"secret":self.secret})}',headers={'Accept':'application/json'})
        try:
            with urlopen(request,timeout=self.timeout_s) as response: payload=json.load(response)
        except (HTTPError,URLError,TimeoutError) as error: raise TigerGraphError('database-secret authentication failed') from error
        token=payload.get('token')
        if payload.get('error') or not token: raise TigerGraphError('database-secret authentication failed')
        self.token=token
        return token
    def _headers(self) -> dict[str,str]:
        headers={'Accept':'application/json'}; token=self._token()
        if token: headers['Authorization']=f'Bearer {token}'
        return headers
    def get_schema(self) -> dict:
        """Read-only schema metadata for connection verification."""
        # GSQL 4.2 accepts a database secret directly for GSQL endpoints.
        # Never log, serialize, or return this header.
        headers={'Accept':'application/json'}
        if self.secret: headers['Authorization']=f'GSQL-Secret {self.secret}'
        elif self.token: headers['Authorization']=f'Bearer {self.token}'
        try:
            with urlopen(Request(f'{self.host}/gsql/v1/schema/graphs/{self.graph_name}',headers=headers),timeout=self.timeout_s) as response: payload=json.load(response)
        except (HTTPError,URLError,TimeoutError) as error: raise TigerGraphError('schema retrieval failed') from error
        if payload.get('error'): raise TigerGraphError('schema retrieval failed')
        return payload
    def try_get_schema(self) -> dict | None:
        """Optional capability check; a timeout never changes REST++ connection state."""
        try: return self.get_schema()
        except TigerGraphError: return None
    def verify_graph(self) -> dict:
        """Read-only RESTPP graph check; returns no data beyond endpoint metadata."""
        try:
            with urlopen(Request(self._restpp_url(f'graph/{self.graph_name}/vertices'),headers=self._headers()),timeout=self.timeout_s) as response: payload=json.load(response)
        except (HTTPError,URLError,TimeoutError) as error: raise TigerGraphError('graph verification failed') from error
        if payload.get('error'): raise TigerGraphError(f'graph verification failed: {payload.get("message", "unknown TigerGraph error")}')
        return payload
    def _query(self,name:str,**parameters:object)->QueryResponse:
        url=f'{self._restpp_url(f"query/{self.graph_name}/{name}")}?{urlencode(parameters)}'; headers=self._headers()
        try:
            with urlopen(Request(url,headers=headers),timeout=self.timeout_s) as response: payload=json.load(response)
        except (HTTPError,URLError,TimeoutError) as error: raise TigerGraphError(f'{name}: request failed') from error
        if payload.get('error'): raise TigerGraphError(f'{name}: {payload.get("message", payload)}')
        return QueryResponse(name=name,data=payload.get('results',[]))
    def get_customer_history(self, customer_id: str, start_ts: str, end_ts: str):
        return self._query(
            'customer_transactions',
            customer=customer_id,
            start_ts=start_ts,
            end_ts=end_ts
        )
    def get_device_neighbors(self,device_profile_id:str,limit:int=100): return self._query('device_neighbors',device=device_profile_id,limit=limit)
    def get_shared_device_transactions(self,device_profile_id:str,limit:int=100): return self._query('shared_device_transactions',device=device_profile_id,limit=limit)
    def get_prior_cases(self,card_id:str,limit:int=100): return self._query('prior_case_neighbors',card=card_id,limit=limit)
    def get_card_connected_cases(self,card_id:str,limit:int=100): return self._query('card_connected_cases',card=card_id,limit=limit)
    def get_case_context(self,case_id:str,limit:int=100): return self._query('case_context',investigation_case=case_id,limit=limit)
    def get_transaction_sequence(self,transaction_id:str,limit:int=20): return self._query('transaction_sequence',transaction=transaction_id,limit=limit)
    def get_region_transactions(self,region_id:str,limit:int=100): return self._query('region_transactions',region=region_id,limit=limit)
    def get_email_transactions(self,email_domain:str,limit:int=100): return self._query('email_transactions',email=email_domain,limit=limit)
    def get_customer_transactions(self,customer_id:str,start_ts:str,end_ts:str,limit:int=100): return self._query('customer_transactions',customer=customer_id,start_ts=start_ts,end_ts=end_ts,limit=limit)
    def get_transaction_context(self,transaction_id:str,limit:int=100): return self._query('transaction_context',transaction=transaction_id,limit=limit)
    def get_connected_cards_from_case(self,case_id:str,limit:int=100): return self._query('connected_cards_from_case',closed_case=case_id,limit=limit)
    def write_case(self,request:WriteCaseRequest): raise TigerGraphError('write_case is intentionally pending Phase 5 graph mutation approval')
