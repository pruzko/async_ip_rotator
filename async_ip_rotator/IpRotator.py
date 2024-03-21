import asyncio
import itertools
import logging

from urllib.parse import urlparse

import aioboto3
from botocore.exceptions import ClientError



class _API:
    '''Represents an API entity.'''

    def __init__(self, id, region, target):
        '''
        Constructor.

        Params:
            id (str|None): The ID of the API.
            region (str|None): The AWS region where the API is located.
            target (str|None): The target URL for the API.
        '''
        self.id = id
        self.region = region
        self.target = target


    @property
    def host(self):
        '''
        Get the host URL for the API.

        Returns:
            str: The host URL.
        '''
        return f'{self.id}.execute-api.{self.region}.amazonaws.com'



class IpRotator:
    '''
    A class for managing IP rotation using AWS API Gateway.

    Attributes:
        DEFAULT_REGION (list): Regions in EU and US.
        EXTRA_REGION (list): DEFAULT_REGIONS plus Asia and South America.
        ALL_REGIONS (list): EXTRA_REGIONS plus regions that require manual opt-in in AWS.
    '''

    DEFAULT_REGIONS = [
        'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'eu-west-1', 'eu-west-2', 'eu-west-3',
        'eu-central-1', 'ca-central-1'
    ]

    EXTRA_REGIONS = DEFAULT_REGIONS + [
        'ap-south-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
        'ap-northeast-1', 'sa-east-1'
    ]

    ALL_REGIONS = EXTRA_REGIONS + [
        'ap-east-1', 'af-south-1', 'eu-south-1', 'me-south-1', 'eu-north-1'
    ]


    def __init__(self, target, aws_key_id, aws_key_secret, regions=None):
        '''
        Constructor.

        Params:
            target (str): The URL of the target website.
            aws_key_id (str): The AWS access key ID.
            aws_key_secret (str): The AWS secret access key.
            regions (list|None): The list of AWS regions to spawn proxies at. None for DEFAULT_REGIONS.
        '''
        target = urlparse(target)
        self.target = f'{target.scheme if target.scheme else "https"}://{target.netloc}'
        self.aws_key_id = aws_key_id
        self.aws_key_secret = aws_key_secret
        self.apis = []
        self.apis_iter = None
        self.regions = regions if regions else self.DEFAULT_REGIONS


    async def __aenter__(self):
        '''
        Enter the context manager and spawn proxies.

        Returns:
            IpRotator: The IpRotator object.
        '''
        tasks = []
        for region in self.regions:
            task = asyncio.create_task(self._create_api(region))
            tasks.append(task)

        self.apis = await asyncio.gather(*tasks)
        self.apis_iter = itertools.cycle(self.apis)

        return self


    async def __aexit__(self, *args, **kwargs):
        '''Exit the context manager and delete proxies.'''
        tasks = []
        for api in self.apis:
            task = asyncio.create_task(self._delete_api(api))
            tasks.append(task)

        await asyncio.gather(*tasks)
        self.apis_iter = None


    async def clear_existing_apis(self):
        '''Search through existing Async IP Rotator APIs and delete them.'''
        for region in self.regions:
            await self._clear_existing_apis(region)


    async def _clear_existing_apis(self, region):
        '''
        Search through existing Async IP Rotator APIs and deletes them.

        Params:
            region (str): The region with the APIs.
        '''
        aws_client = aioboto3.Session().client(
            service_name='apigatewayv2',
            region_name=region,
            aws_access_key_id=self.aws_key_id,
            aws_secret_access_key=self.aws_key_secret,
        )
        async with aws_client as aws_client:
            next_token = None
            apis = []

            res = await aws_client.get_apis(MaxResults='100')
            apis.extend(res['Items'])
            while 'NextToken' in res:
                res = await aws_client.get_apis(MaxResults='100', NextToken=next_token)
                apis.extend(res['Items'])

            apis = [a for a in apis if a['Name'] == 'Async IP Rotator']
            apis = [_API(a['ApiId'], aws_client.meta.region_name, self.target) for a in apis]

        for api in apis:
            await self._delete_api(api)


    async def _create_api(self, region):
        '''
        Create an API proxy.

        Params:
            region (str): The region of the API.

        Returns:
            _API: The _API object.
        '''
        logging.info(f'Creating API for "{region}"')

        aws_client = aioboto3.Session().client(
            service_name='apigatewayv2',
            region_name=region,
            aws_access_key_id=self.aws_key_id,
            aws_secret_access_key=self.aws_key_secret,
        )
        async with aws_client as aws_client:
            api = _API(None, region, self.target)
            res = await aws_client.create_api(
                Name='Async IP Rotator',
                ProtocolType='HTTP',
                Target=self.target,
                CorsConfiguration={
                    'AllowOrigins': ['*'],
                    'AllowMethods': ['*'],
                    'AllowHeaders': ['*'],
                },
            )
            api.id = res['ApiId']

            try:
                await aws_client.create_stage(
                    ApiId=api.id,
                    StageName='ProxyStage',
                )
            except aws_client.exceptions.ConflictException:
                pass

            await aws_client.create_deployment(
                ApiId=api.id,
                StageName='ProxyStage'
            )

            return api


    async def _delete_api(self, api):
        '''
        Delete an API proxy.

        Params:
            api (_API): The API to delete.
        '''
        logging.info(f'Deleting API for "{api.region}"')

        aws_client = aioboto3.Session().client(
            service_name='apigatewayv2',
            region_name=api.region,
            aws_access_key_id=self.aws_key_id,
            aws_secret_access_key=self.aws_key_secret,
        )
        async with aws_client as aws_client:
            while True:
                try:
                    await aws_client.delete_api(ApiId=api.id)
                    return
                except ClientError as e:
                    if e.response['Error']['Code'] == 'TooManyRequestsException':
                        await asyncio.sleep(5)
                        continue
                    raise e
