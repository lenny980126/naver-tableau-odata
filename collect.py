import os #operating system 직접 실행할 수 있도록 도와줌
import requests #정보주고 값을 받을 수 있도록 도와줌
import xml.etree.ElementTree as ET #xml 파일로 형변환 할 수 있도록 도와줌

from pathlib import Path
from dotenv import load_dotenv #.env 파일을 가져올 수 있도록 도와줌

load_dotenv()

URL = "https://naverapihub.apigw.ntruss.com/search/v1/blog"

headers = {
    "X-NCP-APIGW-API-KEY-ID": os.getenv("X-NCP-APIGW-API-KEY-ID"),
    "X-NCP-APIGW-API-KEY": os.getenv("X-NCP-APIGW-API-KEY")
}

params = {
    "query": "에버랜드",
    "display": 100,
    "start": 1,
    "sort": "date",
    "format": "xml"
}

response = requests.get(
    URL,
    headers=headers, 
    params=params, 
    timeout=20
)

root =ET.fromstring(response.content)

items = root.findall("./channel/item")

path = Path("data/naver_blog.xml")
path.write_bytes(response.content)

for item in items[:3] :
    print({
        "title": item.findtext("title"),
        "bloggername": item.findtext("bloggername"),
        "postdate": item.findtext("postdate")
    })