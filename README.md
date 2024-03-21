Async IP Rotator is an IP obfuscating library that integrates with [AioHttp](https://github.com/aio-libs/aiohttp). The library proxies your requests through AWS gateways, leveraging their pool of IP addresses. This allows you to send request from different IPs and bypass IP-based rate-limits of web services.

The library is designed to provide an `async` alternative to the amazing [requests-ip-rotator](https://github.com/Ge0rg3/requests-ip-rotator).


## Installation
To install Async IP Rotator, simply run:
```
pip3 install async-ip-rotator
```


## Usage
```python
import asyncio
import logging

from async_ip_rotator import IpRotator, ClientSession

# set logging to get information about API creation and deletion
logging.basicConfig(level=logging.INFO)

async def main():
    ip_rotator = IpRotator(
        target='https://ipinfo.io',             # target website
        aws_key_id='your_aws_key_id',           # AWS key id
        aws_key_secret='your_aws_key_secret',   # AWS key secret
        regions=['eu-central-1'],               # regions (see IpRotator.py)
        # regions=IpRotator.DEFAULT_REGIONS,
        # regions=IpRotator.EXTRA_REGIONS,
        # regions=IpRotator.ALL_REGIONS,
    )

    # we can optionally delete all existing Async IP Rotator gateways
    # to make sure there are no leftovers from previous failed teardowns
    await ip_rotator.clear_existing_apis()

    async with ip_rotator as ip_rotator:
        async with ClientSession(ip_rotator) as sess:
            for _ in range(4):
                res = await sess.get('https://ipinfo.io/json')
                text = await res.text()
                print(text)

if __name__ == '__main__':
    asyncio.run(main())
```


## Creadit
The library is inspired by [Ge0rg3's](https://github.com/Ge0rg3) [requests-ip-rotator](https://github.com/Ge0rg3/requests-ip-rotator), which is based on [IPRotate_Burp_Extension](https://github.com/RhinoSecurityLabs/IPRotate_Burp_Extension) developed by [RhinoSecurityLabs](https://github.com/RhinoSecurityLabs).
