import aiohttp
import asyncio
import async_timeout
import time
from bs4 import BeautifulSoup

AAA = [] 
 
async def fetch_coroutine(client, url):
    with async_timeout.timeout(10):
        async with client.get(url) as response:
            assert response.status == 200  ## 如果server端成功回應
            html = await response.text()  ##  取得html檔
            soup = BeautifulSoup(html ,'lxml')  ## 透過bs解析html
            As = soup.find_all('a')
            for a in As:
                try:
                    print(a)
                except:
                    print("----------------------------------Error------------------------------------")
            return await response.release()
 
 
async def main(loop):
    urls = ['http://python.org',
            'http://python.org',
            'http://python.org',
            'http://python.org',
            'http://python.org']
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}
 
    async with aiohttp.ClientSession(loop=loop, headers=headers, conn_timeout=5 ) as client:
        tasks = [fetch_coroutine(client, url) for url in urls]  ##整理要執行的task(執行很多次fetch_coroutine function)
        await asyncio.gather(*tasks)  ## 把所有task打包
 
 
if __name__ == '__main__':  ## 如果這支程式是自己直接被執行，而不是透過其他python程式來呼叫，
    startTime = time.time()
    loop = asyncio.get_event_loop()  ## 首先建立一個loop物件
    loop.run_until_complete(main(loop))  ## 透過run_until_complete方法執行Main function
    finishTime = time.time()
    print(finishTime - startTime)
    print(AAA)