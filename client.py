import aiohttp
import asyncio

# headers = {'content-type': 'text/html'}

HOST = 'http://127.0.0.1:8080'

async def make_request(path, method='get', **kwargs):
    async with aiohttp.ClientSession() as session:
        request_method = getattr(session, method)
        async with request_method(f'{HOST}/{path}', **kwargs) as response:
            return (await response.json(content_type='text/html'))


async def main():
    response = await make_request('ads', 'post', json={'ads_name': 'asd name',
                                                       'description': 'asd description',
                                                       'date_create': '2021-12-19 00:00:00.000000',
                                                       'id_owner': '1'})
    print(response)


asyncio.run(main())