"""Mock of a HubSpot-style CRM API for the tenant "acme".

Same shape as the real thing: objects wrapped in {"id", "properties"},
cursor pagination through paging.next.after, at most 100 rows per page.
"""
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data")) / "acme"
OBJECTS = ("companies", "deals")

app = FastAPI(title="Acme CRM (HubSpot-like mock)")


@app.get("/crm/v3/objects/{obj}")
def list_objects(obj: str, limit: int = Query(100, ge=1, le=100), after: int = Query(0, ge=0)):
    if obj not in OBJECTS:
        raise HTTPException(404, f"unknown object '{obj}'")
    path = DATA_DIR / f"{obj}.json"
    if not path.exists():
        raise HTTPException(503, "source data not generated yet")
    rows = json.loads(path.read_text(encoding="utf-8"))
    page = rows[after:after + limit]
    body = {"results": [{"id": r["id"], "properties": {k: v for k, v in r.items() if k != "id"}} for r in page]}
    if after + limit < len(rows):
        body["paging"] = {"next": {"after": str(after + limit)}}
    return body
