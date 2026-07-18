"""
Deal Scanner — FastAPI backend
Serves the SPA and exposes /api/scan for bot-driven deal searches.
"""
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from bots import scan_categories, KNOWN_CATEGORIES

app = FastAPI(title="Deal Scanner Bot")

STATIC = Path(__file__).parent / "static"


class ScanRequest(BaseModel):
    categories: list[str]
    query: str = ""


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/categories")
async def get_categories():
    return {"categories": sorted(KNOWN_CATEGORIES)}


@app.post("/api/scan")
async def scan(req: ScanRequest):
    if not req.categories:
        raise HTTPException(status_code=400, detail="Select at least one category")
    if len(req.categories) > 12:
        raise HTTPException(status_code=400, detail="Maximum 12 categories per scan")

    # Reject any category name not in our known set
    unknown = [c for c in req.categories if c not in KNOWN_CATEGORIES]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown categories: {', '.join(unknown)}",
        )

    try:
        results = await scan_categories(req.categories, req.query.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scan error: {exc}") from exc

    flat: list[dict] = []
    for deals in results.values():
        flat.extend(deals)

    return JSONResponse({"deals": flat, "total": len(flat)})


# Mount static files AFTER route definitions so routes are never shadowed
app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
