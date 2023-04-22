from pydantic import BaseModel
from typing import Union, List, Dict
import json
import datetime
import enum

class FireProxStatus(str, enum.Enum):
    CREATED: str = "CREATED"
    DELETED: str = "DELETED"
    UPDATED: str = "UPDATED"
    RUNNING: str = "RUNNING"    

class FireProxObject(BaseModel):
    def __str__(self):
        """
        Returns the string comprehension of the object.
        """
        return (f"[{self.status}][API ID: {self.api_id}] {self.url} => {self.proxy_url}")
    
    def json(self):
        """
        Returns the JSON string 
        """
        tmp = self.copy().dict()
        keys = tmp.keys() 
        if 'created_at' in keys:
            if isinstance(tmp['created_at'],datetime.datetime):
                tmp['created_at'] = tmp['created_at'].__str__()
        return json.dumps(tmp)
    
class FireProxObjectGeneric(FireProxObject):
    data: Union[str,List,None]
    error: Union[str,None]

class FireProxResourceTag(BaseModel):
    key: str 
    val: str 

class FireProxOwner(str): pass  

class FireProxResponse(FireProxObject):
    id: str
    name: str 
    createdDate: Union[datetime.datetime,str]
    version: Union[str,None] 
    url: str 
    resource_id: Union[str,None]
    proxy_url: str 
    status: FireProxStatus
    tags: List[FireProxResourceTag] = []
    owner: Union[str,None] = None 

    def Owner(self):
        return self.owner
    
    def SetStatus(self, status: FireProxStatus) -> None:
        self.__dict__.update({'status':status})

class FireProxDeploymentResponse(FireProxObject):
    id: str
    description: Union[str,None] = None
    createdDate: Union[datetime.datetime,str]
    apiSummary: Dict = {}
    executeEndpoint: str = ""

    def SetExecuteEndpoint(self, id: str, region: str ):
        self.executeEndpoint = f'https://{id}.execute-api.{region}.amazonaws.com/fireprox/'