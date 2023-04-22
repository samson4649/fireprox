#!/usr/bin/env python3 

from typing import List, Dict, Union
import tldextract
import datetime
import time
import re

from firemod import (
    error,
    types,
    auth,
)

class FireProx(object):
    def __init__(self, auth: auth.BaseAuth):
        """
        Initialise FireProxy
        
        :param auth: FireProx authentication type
        """
        self.session = auth.GetSession()
        self.sts = self.session.client('sts')
        self.client = self.session.client('apigateway')
        self.clientv2 = self.session.client('apigatewayv2')
        self.region = self.client._client_config.region_name

    def __str__(self):
        """
        Return string representation of the FireProx
        """
        return 'FireProx()'

    def TestAuth(self):
        identity = self.sts.get_caller_identity()
        if 'botocore-session-' in identity["Arn"]:
            return True 
        return False
    
    def GetAWSAccount(self) -> int:
        return int(self.sts.get_caller_identity().get('Account'))

    def get_template(self,url):
        """
        Returns a templated swagger file based on the url provided.

        :param url: URL to inject into template.
        """
        if url[-1] == '/':
            url = url[:-1]

        title = 'fireprox_{}'.format(
            tldextract.extract(url).domain
        )
        version_date = f'{datetime.datetime.now():%Y-%m-%dT%XZ}'
        template = '''
        {
          "swagger": "2.0",
          "info": {
            "version": "{{version_date}}",
            "title": "{{title}}"
          },
          "basePath": "/",
          "schemes": [
            "https"
          ],
          "paths": {
            "/": {
              "get": {
                "parameters": [
                  {
                    "name": "proxy",
                    "in": "path",
                    "required": true,
                    "type": "string"
                  },
                  {
                    "name": "X-My-X-Forwarded-For",
                    "in": "header",
                    "required": false,
                    "type": "string"
                  }
                ],
                "responses": {},
                "x-amazon-apigateway-integration": {
                  "uri": "{{url}}/",
                  "responses": {
                    "default": {
                      "statusCode": "200"
                    }
                  },
                  "requestParameters": {
                    "integration.request.path.proxy": "method.request.path.proxy",
                    "integration.request.header.X-Forwarded-For": "method.request.header.X-My-X-Forwarded-For"
                  },
                  "passthroughBehavior": "when_no_match",
                  "httpMethod": "ANY",
                  "cacheNamespace": "irx7tm",
                  "cacheKeyParameters": [
                    "method.request.path.proxy"
                  ],
                  "type": "http_proxy"
                }
              }
            },
            "/{proxy+}": {
              "x-amazon-apigateway-any-method": {
                "produces": [
                  "application/json"
                ],
                "parameters": [
                  {
                    "name": "proxy",
                    "in": "path",
                    "required": true,
                    "type": "string"
                  },
                  {
                    "name": "X-My-X-Forwarded-For",
                    "in": "header",
                    "required": false,
                    "type": "string"
                  }
                ],
                "responses": {},
                "x-amazon-apigateway-integration": {
                  "uri": "{{url}}/{proxy}",
                  "responses": {
                    "default": {
                      "statusCode": "200"
                    }
                  },
                  "requestParameters": {
                    "integration.request.path.proxy": "method.request.path.proxy",
                    "integration.request.header.X-Forwarded-For": "method.request.header.X-My-X-Forwarded-For"
                  },
                  "passthroughBehavior": "when_no_match",
                  "httpMethod": "ANY",
                  "cacheNamespace": "irx7tm",
                  "cacheKeyParameters": [
                    "method.request.path.proxy"
                  ],
                  "type": "http_proxy"
                }
              }
            }
          }
        }
        '''
        template = template.replace('{{url}}', url)
        template = template.replace('{{title}}', title)
        template = template.replace('{{version_date}}', version_date)

        return str.encode(template)
    
    def _build_response(self, item: dict, status: types.FireProxStatus = types.FireProxStatus.RUNNING) -> types.FireProxResponse:
        id = item['id']
        item['k_tags'] = item.pop('tags') if 'tags' in item else []
        return types.FireProxResponse(
            url = f'https://{id}.execute-api.{self.region}.amazonaws.com/fireprox/',
            proxy_url = self._do_get_integration(id)['uri'].replace('{proxy}', '') if status != types.FireProxStatus.DELETED else "",
            status = status,
            tags = [types.FireProxResourceTag(key=k,val=item['k_tags'][k]) for k in item['k_tags']] if 'k_tags' in item else [],
            **(item))

    def _do_create_deployment(self, id: str, variables: Union[Dict,None] = None):
        """
        (Actual) Creates AWS API Gateway deployment.

        :param id: The id of the api gateway deployment.
        """
        if not variables: 
            variables = {} 

        return self.client.create_deployment(
            restApiId=id,
            stageName='fireprox',
            stageDescription='FireProx Prod',
            description='FireProx Production Deployment',
            cacheClusterEnabled=False,
            variables=variables,
        )

    def _do_get_resource(self, id: str) -> dict:
        """
        Returns the AWS API Gateway ID of the resource 

        :param id: The AWS API Gateway ID to fetch
        """
        for item in self.client.get_resources(restApiId=id)['items']:
            item_path = item['path']
            if item_path == '/{proxy+}':
                return item
        return None

    def _do_get_integration(self, id: str):
        """
        Return the URI for the provided API ID

        :param id: AWS API Gateway ID
        """
        return self.client.get_integration(
            restApiId=id,
            resourceId=self._do_get_resource(id)['id'],
            httpMethod='ANY'
        )
    
    def _do_delete_api(self, id: str):
        """
        Delete the requested AWS API Gateway by ID.

        :param id: AWS API Gateway ID
        """
        item = self._do_get_api(id)
        self.client.delete_rest_api(
            restApiId=id,
        )
        return item

    def _do_get_api(self, id: str) -> types.FireProxResponse:
        """
        Return the requested AWS API Gateway by ID.
        """
        return self.client.get_rest_api(restApiId=id)

    def _do_get_apis(self):
        """
        Return a list of AWS API Gateways currently configured.
        """
        resp = []
        for page in self.client.get_paginator('get_rest_apis').paginate():
            for item in page['items']:
                if 'tags' in item:
                    if 'owner' in item['tags'].keys():
                        item['owner'] = item['tags']['owner']
                resp.append(item)
        return resp
    
    def _do_update_api_tag(self, id: str, tags: dict):
        print('not yet implemented')
        return 

    def Create(self, url, owner: types.FireProxOwner = None):
        """
        (Pseudo) Create AWS API Gateway with provided URL

        :param url: The URL used to create the AWS API Gateway
        """
        template = self.get_template(url)
        response = self._build_response(
            self.client.import_rest_api(
                parameters={
                    'endpointConfigurationTypes': 'REGIONAL'
                },
                body=template
            )
        )
        if owner:
            tag_resp = self._do_update_api_tag(
                id = response.id,
                tags = {
                    "owner": owner,
                }
            )

        deployment = types.FireProxDeploymentResponse(
            **self._do_create_deployment(response.id)
        )
        deployment.SetExecuteEndpoint(id=response.id,region=self.region)
        
        return types.FireProxResponse(
            id = response.id,
            createdDate = response.createdDate,
            name = response.name,
            proxy_url = url,
            resource_id = deployment.id,
            status = types.FireProxStatus.CREATED,
            url = deployment.executeEndpoint,
            version = response.version,
        )
    
    def Tag(self, api_id: int, owner: types.FireProxOwner) -> types.FireProxResponse:
        arn = f'arn:{self.GetAWSAccount()}:apigateway:{self.region}::/apis/{api_id}'
        print(arn)
        response = self.client.tag_resource(
            resourceArn=arn,
            tags={
                'owner': owner,
            }
        )
        
    def Update(self, api_id: int, url: str) -> types.FireProxResponse:
        """
        (Actual) Update AWS API Gateway with provided URL

        :param id: AWS API Gateway ID 
        :param url: The URL used to create the AWS API Gateway
        """
        if not any([api_id, url]):
            raise error.FireProxConfigException('Please provide a valid API ID and URL end-point')

        if url[-1] == '/':
            url = url[:-1]

        resource_id = self._do_get_resource(api_id)['id']
        if resource_id:
            # print(f'Found resource {resource_id} for {api_id}!')
            response = self.client._do_update_integration(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='ANY',
                patchOperations=[
                    {
                        'op': 'replace',
                        'path': '/uri',
                        'value': '{}/{}'.format(url, r'{proxy}'),
                    },
                ]
            )
            # print(response)
            # return response['uri'].replace('/{proxy}', '') == url
            return types.FireProxResponse(
                api_id=api_id,
                url=url,
            )
        else:
            raise error.FireProxConfigException(f'Unable to update, no valid resource for {api_id}')

    def Get(self, id: str) -> types.FireProxResponse:
        """
        (Pseudo) Get single AWS API Gateway based on provided ID

        :param id: The AWS API Gateway ID to get.
        """

    def Delete(self, id: str) -> List[types.FireProxResponse]:
        """
        (Pseudo) Delete AWS API Gateway based on provided ID

        :param id: The AWS API Gateway ID to delete.
        """
        return self._build_response(
            self._do_delete_api(id), 
            status=types.FireProxStatus.DELETED
        )
    
    def List(self, owner: Union[str,None] = None) -> List[types.FireProxResponse]:
        """
        (Pseudo) List AWS API Gateways

        :returns: List of FireProxyResponses
        :rtype: List[types.FireProxyResponse]
        :raises error.FireProxConfigException: If configuration is wrong.
        """
        resp = []
        for item in self._do_get_apis():
            try:
                resp.append(
                    self._build_response(item=item)
                )
            except:
                raise error.FireProxConfigException("Error listing gateways")

        if owner:
            return list(filter(lambda x: re.match(owner, x.Owner(), resp ) ))
                          
        return resp
        
    def DeleteAll(self) -> List:
        """
        -- NOT CURRENTLY IN USE --
        """
        return []
        resp = []
        items = self.client.get_rest_apis()['items']
        print(items)
        for item in items:
            api_id = item['id']
            print(f"[Deleting: {api_id}]")
            response = self.client.delete_rest_api(
                restApiId=api_id,
            )
            resp.append(response)
            # self.Delete(id = a.api_id)
            time.sleep(3)
        return resp 
        