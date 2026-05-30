"""STRATEX™ shared core — app, db, routers, dependencies, common helpers.

All route modules import their FastAPI app, db client, routers, and auth
dependencies from this module. This is the only place where the FastAPI
`app`, MongoDB client, and shared APIRouters are constructed.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from stratex_auth import auth_dep, role_dep, require_nda  # noqa: E402

# --- Mongo --------------------------------------------------------------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]


def get_db():
    return db


# --- App + routers ------------------------------------------------------
app = FastAPI(title="STRATEX API", version="2.0.0")
api = APIRouter(prefix="/api")
auth_r = APIRouter(prefix="/api/auth")

logger = logging.getLogger("stratex")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Auth dependency singletons (bound to local db) ---------------------
current_user = auth_dep(get_db)
contractor_only = role_dep(get_db, "contractor")
operator_only = role_dep(get_db, "operator")
admin_only = role_dep(get_db, "admin")
contractor_ndaed = require_nda(get_db)


# --- Shared response shapers --------------------------------------------
def _public_user(u: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": u["id"],
        "email": u["email"],
        "legal_name": u.get("legal_name", ""),
        "first_name": u.get("first_name") or (
            u.get("legal_name", "").split(" ")[0] if u.get("legal_name") else ""
        ),
        "company_name": u.get("company_name", ""),
        "role": u["role"],
        "tour_mode": bool(u.get("tour_mode", False)),
        "nda_accepted": u.get("nda_accepted", False),
        "totp_enrolled": u.get("totp_enrolled", False),
        "created_at": u.get("created_at"),
    }


def _strip_pricing(job: Dict[str, Any]) -> Dict[str, Any]:
    """Operator/operator-board view: redact ALL pricing & business fields."""
    o = dict(job)
    o.pop("pricing", None)
    o.pop("homeowner_email", None)
    o.pop("homeowner_phone", None)
    return o
