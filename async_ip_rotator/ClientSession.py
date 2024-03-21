from urllib.parse import urlparse

import aioboto3
import aiohttp



class ClientSession(aiohttp.ClientSession):
    '''AioHttp ClientSession that proxies requests through the IpRotator'''
    def __init__(self, rotator, *args, **kwargs):
        '''
        Constructor.

        Params:
            rotator (IpRotator): The IpRotator object.

        See aiohttp.ClientSession
        '''
        self.rotator = rotator
        super().__init__(*args, **kwargs)


    async def _request(self, method, url, *args, **kwargs):
        '''See aiohttp.ClientSession._request'''
        if kwargs.get('headers', {}).get('Upgrade', None) == 'websocket':
            return await super()._request(method, url, *args, **kwargs)

        url = urlparse(url)
        url = url.path if not url.query else f'{url.path}?{url.query}'
        url = url.lstrip('/')
        api_url = f'https://{next(self.rotator.apis_iter).host}/ProxyStage/{url}'

        return await super()._request(method, api_url, *args, **kwargs)
