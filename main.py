import re
import json
import html
import xml.etree.ElementTree as ET

from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response

app = FastAPI(title="Naver Blog OData API")

DATA_FILE = Path(__file__).parent / "data" / "naver_blog.xml"

def load_blogs():
  root = ET.parse(DATA_FILE).getroot()
  blogs = list()

  for index, item in enumerate(
    root.findall("./channel/item"), 1
  ):
    title = item.findtext("title", "")
    title = re.sub(r"<[^>]+>", "", html.unescape(title))

    blogs.append({
      "ID": index,
      "Title": title,
      "BloggerName": item.findtext("bloggername", ""),
      "PostDate": item.findtext("postdate", ""),
      "Link": item.findtext("link", ""),
    })

  return blogs

def base_url(request):
  return str(request.base_url).rstrip("/") + "/odata/"

# API (xml) -> Tableau (insert) -> 시각화 (A = bar, B = pie, C) json
# xml > json
# 프론트엔드, 백엔드 개념

def odata_json(data):
  return Response(
    content=json.dumps(data, ensure_ascii=False),
    media_type="application/json",
    headers={"OData-Version": "4.0"}
  )

@app.get("/")
def home():
  return {
    "status": "running",
    "service": "/odata",
    "metadata": "/odata/$metadata",
    "data": "/odata/Blogs"
  }

@app.get("/odata/")
def service_root(request: Request):
  return odata_json({
    "@odata.context": base_url(request) + "$metadata",
    "value": [
      {
        "name": "Blogs",
        "kind": "EntitySet",
        "url": "Blogs"
      }
    ]
  })

@app.get("/odata/$metadata")
def metadata():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="4.0"
 xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
  <edmx:DataServices>
    <Schema Namespace="Naver"
      xmlns="http://docs.oasis-open.org/odata/ns/edm">

      <EntityType Name="Blog">
        <Key>
          <PropertyRef Name="ID"/>
        </Key>
        <Property Name="ID"
          Type="Edm.Int32" Nullable="false"/>
        <Property Name="Title" Type="Edm.String"/>
        <Property Name="BloggerName" Type="Edm.String"/>
        <Property Name="PostDate" Type="Edm.String"/>
        <Property Name="Link" Type="Edm.String"/>
      </EntityType>

      <EntityContainer Name="Container">
        <EntitySet Name="Blogs"
          EntityType="Naver.Blog"/>
      </EntityContainer>

    </Schema>
  </edmx:DataServices>
</edmx:Edmx>"""

    return Response(
        content=xml,
        media_type="application/xml",
        headers={"OData-Version": "4.0"}
    )

@app.get("/odata/Blogs")
def get_blogs(request: Request):
    blogs = load_blogs()
    params = request.query_params

    # Tableau 및 일반 OData 클라이언트의 기본 조회 옵션
    try:
        skip = int(params.get("$skip", "0"))
        top = int(params.get("$top", str(len(blogs))))
    except ValueError:
        raise HTTPException(400, "Invalid pagination")

    if skip < 0 or top < 0:
        raise HTTPException(400, "Invalid pagination")

    total = len(blogs)

    # 기본 정렬
    orderby = params.get("$orderby")
    if orderby:
        parts = orderby.split()
        field = parts[0]
        if field not in blogs[0] if blogs else False:
            raise HTTPException(400, "Unknown field")
        if len(parts) > 2 or (
            len(parts) == 2 and parts[1] not in ("asc", "desc")
        ):
            raise HTTPException(400, "Invalid orderby")
        if blogs:
            blogs.sort(
                key=lambda x: x[field],
                reverse=len(parts) == 2 and parts[1] == "desc"
            )

    blogs = blogs[skip:skip + top]

    result = {
        "@odata.context": base_url(request) + "$metadata#Blogs",
        "value": blogs
    }

    if params.get("$count", "").lower() == "true":
        result["@odata.count"] = total

    return odata_json(result)

@app.get("/odata/Blogs/$count")
def count_blogs():
    return Response(
        content=str(len(load_blogs())),
        media_type="text/plain",
        headers={"OData-Version": "4.0"}
    )

@app.get("/odata/Blogs({blog_id})")
def get_blog(blog_id: int, request: Request):
    blog = next(
        (b for b in load_blogs() if b["ID"] == blog_id),
        None
    )

    if blog is None:
        raise HTTPException(404, "Blog not found")

    return odata_json({
        "@odata.context": base_url(request) + "$metadata#Blogs/$entity",
        **blog
    })