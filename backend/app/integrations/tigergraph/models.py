from pydantic import BaseModel, Field
class QueryRequest(BaseModel): name:str; parameters:dict[str,object]=Field(default_factory=dict)
class QueryResponse(BaseModel): name:str; data:object
class WriteCaseRequest(BaseModel): case_id:str; payload:dict[str,object]
