"""
Food Tracker Dashboard - FastAPI Application
Simple web interface to view and edit food log data from Google Sheets.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from dashboard.service import (
    get_all_entries,
    update_entry,
    delete_entry,
    get_entries_paginated
)

app = FastAPI(title="Food Tracker Dashboard")

# Templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


class EntryUpdate(BaseModel):
    """Model for updating a food entry."""
    name: Optional[str] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    portion: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, page: int = 1, per_page: int = 20):
    """Main dashboard page with food log table."""
    result = get_entries_paginated(page=page, per_page=per_page)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "entries": result["entries"],
        "page": result["page"],
        "per_page": result["per_page"],
        "total": result["total"],
        "total_pages": result["total_pages"],
        "has_prev": result["has_prev"],
        "has_next": result["has_next"]
    })


@app.get("/api/entries")
async def api_get_entries(page: int = 1, per_page: int = 20):
    """API endpoint to get paginated entries."""
    return get_entries_paginated(page=page, per_page=per_page)


@app.put("/api/entries/{row_index}")
async def api_update_entry(row_index: int, update: EntryUpdate):
    """API endpoint to update a food entry."""
    update_data = update.dict(exclude_none=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    success = update_entry(row_index, update_data)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update entry")

    return {"success": True, "row": row_index}


@app.delete("/api/entries/{row_index}")
async def api_delete_entry(row_index: int):
    """API endpoint to delete a food entry."""
    success = delete_entry(row_index)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete entry")

    return {"success": True, "row": row_index}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
