"""
Deal Scanner — FastAPI backend
Serves the SPA and exposes /api/scan for bot-driven deal searches.
"""
import asyncio
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from bots import scan_categories, CATEGORY_QUERIES

app = FastAPI(title="Deal Scanner Bot")

STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class ScanRequest(BaseModel):
    categories: list[str]
    query: str = ""


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/categories")
async def get_categories():
    return {"categories": list(CATEGORY_QUERIES.keys())}


@app.post("/api/scan")
async def scan(req: ScanRequest):
    if not req.categories:
        raise HTTPException(400, "Select at least one category")
    if len(req.categories) > 12:
        raise HTTPException(400, "Maximum 12 categories per scan")

    results = await scan_categories(req.categories, req.query.strip())
    flat: list[dict] = []
    for cat, deals in results.items():
        flat.extend(deals)

    return JSONResponse({"deals": flat, "total": len(flat)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
