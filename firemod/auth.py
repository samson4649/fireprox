from pydantic import BaseModel
from typing import Union, List, Dict
import boto3 

class BaseAuth(BaseModel):
    region_name: Union[str,None]
    metadata: Union[Dict,None]
    
class ProfileAuth(BaseAuth):
    profile_name: str

    def GetSession(self) -> boto3.Session:
        """
        Create AWS Boto3 Session (based on objects AWS profile name) and return it.

        :returns: Boto3 Session object
        :rtype: boto3.session.Session
        """
        return boto3.session.Session(**self.dict(include={
            "profile_name",
        }))

class KeyAuth(BaseAuth):
    aws_access_key_id: str 
    aws_secret_access_key: str 
    aws_session_token: Union[str, None]

    def GetSession(self) -> boto3.Session:
        """
        Create AWS Boto3 Session (based on objects AWS keys) and return it.

        :returns: Boto3 Session object
        :rtype: boto3.session.Session
        """
        return boto3.session.Session(**self.dict(include={
            "aws_access_key_id",
            "aws_secret_access_key",
            "aws_session_token",
        }))