import os
import random
import secrets
import string
from datetime import datetime, timezone

import fastapi
import uvicorn
from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

import certifi
ca = certifi.where()

import dotenv

dotenv.load_dotenv()

app = fastapi.FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("/static/favicon.svg")


db_client: AsyncIOMotorClient = None


def get_collection():
    return db_client["glyph"]["pastes"]


@app.on_event("startup")
async def startup():
    global db_client
    db_client = AsyncIOMotorClient(os.environ["MONGODB_URI"], tlsCAFile=ca)


@app.on_event("shutdown")
async def shutdown():
    db_client.close()


class PasteCreate(BaseModel):
    content: str
    language: str = "text"
    filename: str | None = None


@app.get("/")
def index():
    return FileResponse("static/index.html")


ALPHABET = string.ascii_uppercase + string.digits


@app.get("/{paste_id}")
def view(paste_id: str):
    return FileResponse("static/view.html")


@app.get("/{paste_id}/raw")
async def get_paste_raw(paste_id: str):
    doc = await get_collection().find_one({"_id": paste_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Paste not found.")

    return HTMLResponse(doc["content"])


@app.get("/api/paste/{paste_id}")
async def get_paste(paste_id: str):
    doc = await get_collection().find_one({"_id": paste_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Paste not found.")

    return {
        "id": doc["_id"],
        "content": doc["content"],
        "language": doc["language"],
        "filename": doc.get("filename"),
        "created_at": doc["created_at"].isoformat(),
    }


async def generate_paste_id():
    collection = get_collection()

    while True:
        paste_id = "".join(random.choices(ALPHABET, k=5))

        exists = await collection.find_one({"_id": paste_id}, {"_id": 1})

        if not exists:
            return paste_id


@app.post("/api/create")
async def create_paste(body: PasteCreate):
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty.")

    paste_id = await generate_paste_id()
    delete_key = secrets.token_urlsafe(24)

    doc = {
        "_id": paste_id,
        "content": body.content,
        "language": body.language,
        "filename": body.filename,
        "delete_key": delete_key,
        "created_at": datetime.now(timezone.utc),
    }

    await get_collection().insert_one(doc)

    return {
        "id": paste_id,
        "delete_key": delete_key,
        "url": f"/{paste_id}",
    }


@app.delete("/api/paste/{paste_id}")
async def delete_paste(paste_id: str, delete_key: str):
    doc = await get_collection().find_one({"_id": paste_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Paste not found.")
    if doc["delete_key"] != delete_key:
        raise HTTPException(status_code=403, detail="Invalid delete key.")

    await get_collection().delete_one({"_id": paste_id})
    return {"deleted": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
