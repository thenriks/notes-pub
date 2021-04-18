from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import dbcreds
from pymongo import MongoClient
from pymongo.collection import ReturnDocument
import string
import random
import uuid


class TextModel(BaseModel):
    token: str
    text: str


class LinkModel(BaseModel):
    token: str
    url: str


class RemoveBody(BaseModel):
    token: str
    id: str


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"Nothing to see here."}


@app.get("/{item_id}", response_class=HTMLResponse)
async def show_item(item_id: int):
    site_info = await get_site(item_id)

    style = "style=\"background-color: lightblue;margin: 5px\""

    htmlstr = "<html><body>"
    htmlstr += f"<h3>{site_info['title']}</h3>"

    for e in site_info['elements']:
        if e["type"] == 'text':
            htmlstr += f"<div {style}>{e['text']}</div>"
        elif e["type"] == 'link':
            htmlstr += f"<div {style}><a href=\"{e['url']}\" target=\"_blank\">{e['url']}</a></div>"


    htmlstr += "</body><html>"

    return htmlstr


def get_token():
    client = MongoClient(dbcreds.MONGOPATH)
    usrdb = client.userdata
    usrcol = usrdb.users

    token = ''.join(random.choices(string.ascii_letters + string.digits, k=6))

    # Check if token is already in use
    if usrcol.find_one({"token": token}) is None:
        return token

    return get_token()


@app.post("/new")
async def new_site():
    client = MongoClient(dbcreds.MONGOPATH)

    ndb = client.notedata
    ncol = ndb.sites
    infocol = ndb.info
    info = infocol.find_one_and_update({'id': 'count'}, {'$inc': {'count': 1}}, return_document=ReturnDocument.AFTER)
    res = info['count']

    data = {"sid": res, "title": "Title", "isOpen": True, "elements": []}
    ncol.insert_one(data)

    token = get_token()

    usrdb = client.userdata
    usrcol = usrdb.users

    usrcol.insert_one({"token": token, "sid": res})

    return {"token": token, "sid": res}


@app.post("/remove")
async def remove_element(rb: RemoveBody):
    client = MongoClient(dbcreds.MONGOPATH)

    usrcol = client.userdata.users
    usr = usrcol.find_one({"token": rb.token})

    ndb = client.notedata
    ncol = ndb.sites
    site = ncol.find_one({"sid": usr['sid']})

    if site["isOpen"] is False:
        return "ERROR: site closed."

    currentElems = site["elements"]

    elementFound = False
    elementIndex = 0

    for e in currentElems:
        print("id: " + str(e["id"]))
        if str(e["id"]) == str(rb.id):
            elementFound = True
            break
        elementIndex += 1

    if elementFound:
        del currentElems[elementIndex]

    ncol.update_one({"sid": usr['sid']}, {"$set": {"elements": currentElems}})

    return "Success"


@app.get("/site/{site_id}")
async def get_site(site_id: int):

    client = MongoClient(dbcreds.MONGOPATH)
    ndb = client.notedata
    ncol = ndb.sites
    site = ncol.find_one({"sid": site_id})

    return {"title": site["title"], "sid": site["sid"], "isOpen": site["isOpen"], "elements": site["elements"]}


@app.get("/site_id/{token}")
async def get_id(token: str):
    client = MongoClient(dbcreds.MONGOPATH)

    usrcol = client.userdata.users
    usr = usrcol.find_one({"token": token})

    return usr['sid']


@app.post("/add_text")
async def add_text(new_text: TextModel):
    el = {"id": uuid.uuid4(), "type": "text", "text": new_text.text}

    client = MongoClient(dbcreds.MONGOPATH)

    usrcol = client.userdata.users
    usr = usrcol.find_one({"token": new_text.token})

    ndb = client.notedata
    ncol = ndb.sites
    site = ncol.find_one({"sid": usr['sid']})

    if site["isOpen"] is False:
        return "ERROR: site closed."

    currentElems = site["elements"]
    currentElems.append(el)

    ncol.update_one({"sid": usr['sid']}, {"$set": {"elements": currentElems}})

    return "Success"


@app.post("/add_link")
async def add_link(new_link: LinkModel):
    el = {"id": uuid.uuid4(), "type": "link", "url": new_link.url}

    client = MongoClient(dbcreds.MONGOPATH)

    usrcol = client.userdata.users
    usr = usrcol.find_one({"token": new_link.token})

    ndb = client.notedata
    ncol = ndb.sites
    site = ncol.find_one({"sid": usr['sid']})

    if site["isOpen"] is False:
        return "ERROR: site closed."

    currentElems = site["elements"]
    currentElems.append(el)

    ncol.update_one({"sid": usr['sid']}, {"$set": {"elements": currentElems}})

    return "Success"
