# SECURITY_PASSPORT_AUTHORITY_CHECKPOINT.md
# C-P-001C Clean Security Checkpoint

## Scope

This checkpoint contains only:

1. Fail-closed development-authentication containment (`backend/dev_auth.py`)
2. Production hard-locks for TOTP and CEO/SMS debug-code disclosure
3. Dev-login rate limiting with safe audit events
4. Containment of public Legacy Passport mutation routes
5. Containment of claim-snapshot seed and cosign-request mutation
6. Focused deterministic tests
7. The `pyotp` dependency pin required by existing TOTP code

It does **not** include C-P-002 work, frontend DevAuthBar UI, owner/superadmin
bootstrap expansion, preview-host rewrites, generated test reports, or
`.emergent` platform housekeeping.

## Development authentication law

`POST /api/auth/dev/login` and `GET /api/auth/dev/status` are enabled only when
**all** of the following are true:

- `DEV_NO_AUTH` is explicitly truthy (`true` / `1` / `yes` / `on`)
- `APP_ENV` is exactly one of: `local`, `development`, `dev`, `preview`,
  `sandbox`, `test`
- `is_production()` is false

`is_production()` is true when:

- `APP_ENV` is `production`, `prod`, or `live`, **or**
- the hostname token `stratexdrone.com` appears in `CORS_ORIGINS`,
  `PUBLIC_FRONTEND_URL`, `FRONTEND_URL`, or `PROD_HOSTS`

Fail closed when `APP_ENV` is missing, blank, unknown (including `staging`),
or when `DEV_NO_AUTH` is absent/false. Production checks always win over
development flags.

Synthetic identities use `@stratex.dev` emails and unusable random password
hashes. They cannot authenticate through normal password login. Token minting
reuses existing `create_access_token` / `create_refresh_token`.

## Production debug hard-locks

- `GET /api/auth/totp-debug` returns 404 when production **or** when
  `DEMO_MFA_BYPASS` is not `1`
- CEO SMS `debug_code` is surfaced only when `DEMO_SMS_BYPASS=1` **and**
  not production
- Missing bypass flags default disabled
- Invalid MFA verification produces no access token (unchanged login contract)

## Dev-login rate limit

- Endpoint: `POST /api/auth/dev/login`
- Limit: 10 requests / 60 seconds per `request.client.host`
- Does **not** trust `X-Forwarded-For` by default
- Independent IP buckets; stale buckets pruned; hard key cap
- Over-limit → HTTP 429 with `Retry-After`
- Production remains HTTP 403 regardless of limiter state
- Rate-limit audit (`dev_auth.rate_limited`) stores event, timestamp, route,
  method, client host, reason — never passwords, tokens, MFA codes, bodies,
  or Authorization headers

**Deployment limitation:** process-local in-memory limiting is suitable for
local/preview and single-process containment only. It is **not**
distributed-production-safe.

## Legacy Passport mutation containment

Guarded by `require_legacy_passport_writer` (admin, ceo, or an already-present
`is_superadmin` user-document claim — no new global privilege expansion):

- `POST /api/passport/issue`
- `POST /api/passport/{id}/append`
- `POST /api/passport/seed/demo`
- `POST /api/claim-snapshot/seed/{passport_id}`
- `POST /api/claim-snapshot/{passport_id}/cosign/request`

Public read/verify/PDF routes remain read-only.

Blocked attempts return 403 and write a safe audit record to
`legacy_passport_blocked_writes` (path, method, reason, actor, client host,
user id/email when authenticated). No bearer tokens or credentials are stored.

## Claim co-sign governed model

- **Request (mint token):** privileged Legacy writer authority required
- **Submit:** authorized only by a validated, unused, purpose-bound one-time
  token previously minted by a privileged request
- Empty/invalid tokens are rejected; invalid attempts are audited without
  logging the token value
- Anonymous unrestricted mutation is prohibited

## Writer authority

NextGen has one canonical ledger writer:
`nextgen/passport_service.py::append_entry`.

`intelligence.py` and `findings.py` delegate to `append_entry`. Habitat has no
canonical Passport write path.

Legacy compatibility writers remain present. Public Legacy mutation routes
covered by C-P-001C are authenticated and authorization-gated. Internal
background compatibility writers (notably Storm Watcher) remain disclosed and
are not equivalent to the NextGen canonical ledger authority.

## Credential incident

A prior contaminated checkpoint tracked plaintext credentials in generated
test-report artifacts. Those credentials must be treated as compromised.

Owner credential rotation:
**USER ACTION — EXTERNAL VERIFICATION REQUIRED**

GitHub token revocation:
**USER ACTION — EXTERNAL VERIFICATION REQUIRED**

This clean branch starts from `origin/main` and contains none of those values.

## Dependency notes (C-P-001C)

| Dependency | Reason | Evidence |
|---|---|---|
| `pyotp==2.9.0` | Already imported by `stratex_auth` / TOTP debug; missing from lock previously | Backend MFA modules import `pyotp` |
| `PyJWT==2.8.0` | `stratex_auth` imports `jwt`; required for token create/decode | `import jwt` fails without PyJWT |
| `email-validator==2.1.0.post1` | Required by existing Pydantic `EmailStr` signup models for app import | Server import fails without it |

No Playwright. No unrelated dependency additions.

## Exact test commands

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest
export JWT_SECRET=test-jwt-secret-for-local-only
export AES_KEY=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
export MONGO_URL=mongodb://127.0.0.1:27017
export DB_NAME=stratex_cp001c_test
export NEXTGEN_STORAGE_ROOT=/tmp/stratex-nextgen-storage
pytest tests/test_dev_auth.py tests/test_passport_authority.py \
  tests/test_mfa_debug_locks.py tests/test_writer_authority.py -q
```

Optional broader suite (may require live services):

```bash
pytest tests/ -q --ignore=tests/test_iter20_claim_snapshot.py \
  --ignore=tests/test_iter21_cosign.py
```

## Known limitations

- In-memory rate limiter is not shared across processes
- Storm Watcher remains an internal Legacy writer
- Intelligence vs findings separation-of-duties differences are pre-existing
  and out of scope for C-P-001C
- Full `server.py` boot in non-Emergent environments also requires the
  proprietary `emergentintegrations` package and writable paths replacing
  hard-coded `/app/...` defaults (`NEXTGEN_STORAGE_ROOT`, demo samples)
- Production readiness requires Atlas-controlled merge review after external
  credential rotation
