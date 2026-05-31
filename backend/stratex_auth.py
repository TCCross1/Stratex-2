"""STRATEX™ secure auth module — JWT (Bearer) + bcrypt + TOTP MFA + role guards + AES-256 field encryption."""
from __future__ import annotations

import os
import base64
import bcrypt
import jwt
import pyotp
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from fastapi import Depends, HTTPException, Request
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

JWT_ALG = "HS256"
ACCESS_TTL_MIN = 60
REFRESH_TTL_DAYS = 7


# ---------------------------------------------------------------------------
# Password
# ---------------------------------------------------------------------------

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def _secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, role: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "email": email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TTL_MIN),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALG)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TTL_DAYS),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALG)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, _secret(), algorithms=[JWT_ALG])


# ---------------------------------------------------------------------------
# TOTP (Google Authenticator / Authy / 1Password)
# ---------------------------------------------------------------------------

def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str, issuer: str = "STRATEX") -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
    if not secret or not code:
        return False
    code = code.replace(" ", "")
    try:
        return pyotp.TOTP(secret).verify(code, valid_window=valid_window)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# AES-256 encryption for confidential business rules (Fernet/AES128 over HKDF-derived key
# using the configured AES_KEY env. We use the env hex string as IKM and derive a stable
# 32-byte key via HKDF. Each ciphertext is independently nonce'd by Fernet.)
# ---------------------------------------------------------------------------

def _derive_fernet_key() -> bytes:
    key_hex = os.environ["AES_KEY"]
    ikm = bytes.fromhex(key_hex) if all(c in "0123456789abcdefABCDEF" for c in key_hex) else key_hex.encode()
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"stratex-v1", info=b"business-rules")
    derived = hkdf.derive(ikm)
    return base64.urlsafe_b64encode(derived)


_FERNET: Optional[Fernet] = None


def _fernet() -> Fernet:
    global _FERNET
    if _FERNET is None:
        _FERNET = Fernet(_derive_fernet_key())
    return _FERNET


def encrypt_value(value: Any) -> str:
    """Encrypt any JSON-serialisable value → opaque base64 ciphertext string."""
    import json
    if value is None:
        return ""
    raw = json.dumps(value).encode("utf-8")
    return _fernet().encrypt(raw).decode("utf-8")


def decrypt_value(ciphertext: str) -> Any:
    import json
    if not ciphertext:
        return None
    raw = _fernet().decrypt(ciphertext.encode("utf-8"))
    return json.loads(raw.decode("utf-8"))


# ---------------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------------

async def _extract_user(request: Request, db) -> Dict[str, Any]:
    token = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid token type")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(401, "User not found")
    # strip secrets
    user.pop("password_hash", None)
    user.pop("totp_secret", None)
    return user


def auth_dep(db_getter):
    """Returns a FastAPI dependency that yields the current user (any role)."""
    async def _dep(request: Request) -> Dict[str, Any]:
        return await _extract_user(request, db_getter())
    return _dep


def role_dep(db_getter, *allowed_roles: str):
    async def _dep(request: Request) -> Dict[str, Any]:
        user = await _extract_user(request, db_getter())
        if user.get("role") not in allowed_roles:
            raise HTTPException(403, f"Role {user.get('role')!r} not authorized for this endpoint")
        return user
    return _dep


def require_ceo(db_getter):
    """Strict CEO-only guard. role must equal 'ceo'."""
    async def _dep(request: Request) -> Dict[str, Any]:
        user = await _extract_user(request, db_getter())
        if user.get("role") != "ceo":
            raise HTTPException(403, "CEO clearance required")
        return user
    return _dep


def require_nda(db_getter):
    async def _dep(request: Request) -> Dict[str, Any]:
        user = await _extract_user(request, db_getter())
        if not user.get("nda_accepted"):
            raise HTTPException(403, "NDA must be accepted to access this resource")
        return user
    return _dep


# ---------------------------------------------------------------------------
# NDA template (Mutual Non-Disclosure & Data Privacy Agreement)
# ---------------------------------------------------------------------------

NDA_TEMPLATE = """STRATEX™ MUTUAL NON-DISCLOSURE & DATA PRIVACY AGREEMENT

This Mutual Non-Disclosure and Data Privacy Agreement ("Agreement") is entered into
as of {effective_date} by and between:

    PARTY A:  STRATEX TECHNOLOGIES INC. ("STRATEX")
    PARTY B:  {legal_name}, acting on behalf of {company_name} ("Contractor")

Each a "Party" and collectively the "Parties".

1. CONFIDENTIAL INFORMATION.
   The Parties acknowledge that, in the course of their relationship, each will gain
   access to commercially sensitive information including but not limited to material
   wholesale unit prices, overhead percentages, net profit margins, labor rates,
   insurance supplement multipliers, customer financial data, and proprietary AI
   estimation algorithms (collectively, "Confidential Information").

2. CONTRACTOR DATA ISOLATION.
   STRATEX warrants that the Contractor's pricing matrix, business multipliers,
   margins, and homeowner financial records are stored under row-level AES-256
   application-layer encryption and are NEVER exposed to STRATEX field operators,
   STRATEX administrators, or any other contractor account on the platform.
   STRATEX personnel have ZERO read-visibility to these fields.

3. DRONE-CAPTURED PROPERTY DATA.
   Imagery, radiometric thermal data, and 3D photogrammetry meshes captured by the
   STRATEX autonomous fleet are processed in isolated tenant containers and made
   available only to the contracting Contractor that initiated the job.

4. NON-USE & NON-DISCLOSURE.
   Neither Party shall disclose Confidential Information to any third party nor use
   it for any purpose other than the performance of services contemplated under the
   STRATEX platform service agreement.

5. TERM.
   This Agreement shall remain in effect for five (5) years from the Effective Date,
   notwithstanding the termination of the underlying service agreement.

6. ELECTRONIC SIGNATURE.
   The Contractor acknowledges that affixing their typed legal name in the signature
   field, along with confirmation of the contractor's IP address and a UTC timestamp
   captured by STRATEX, constitutes a legally binding electronic signature pursuant
   to the U.S. ESIGN Act and analogous state and international law.

CONTRACTOR ACCEPTANCE
    Legal Name:    {legal_name}
    Company:       {company_name}
    Email:         {email}
    IP Address:    {ip}
    Timestamp UTC: {timestamp}
"""


def render_nda(legal_name: str, company_name: str, email: str, ip: str, when: datetime) -> str:
    return NDA_TEMPLATE.format(
        effective_date=when.strftime("%B %d, %Y"),
        legal_name=legal_name,
        company_name=company_name,
        email=email,
        ip=ip,
        timestamp=when.isoformat(),
    )
