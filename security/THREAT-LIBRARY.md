# Dhwani-Kavach — Security Threat Library

Living catalog of every risk class the product has faced, maintained by the
`security-sentinel` agent (`.claude/agents/security-sentinel.md`). This file is the
agent's **memory**: it reads it at the start of every run and grows it over time.

**How it grows:** each run the agent re-checks every entry, fetches new CVEs/advisories
for the stack, and proposes new or changed entries via a **human-reviewed PR**
(branch `security/threat-library-<date>`). Nothing here is auto-merged.

**Status values:** `ACTIVE` (open risk) · `MITIGATED` (fixed; watch for regression) ·
`ACCEPTED` (deliberate tradeoff, e.g. a demo-only setting — do not re-raise).

**Entry format:**
```
### T-NNN <title>
- Category: <e.g. deserialization, DoS, authn, supply-chain>
- Applies to: <file:line or component>
- Check: <what to verify each run>
- Status: ACTIVE | MITIGATED | ACCEPTED
- First seen: YYYY-MM-DD · Last reviewed: YYYY-MM-DD
- Notes: <evidence / advisory link / fix>
```

---

## Entries

### T-001 Pickle deserialization via `torch.load`
- Category: deserialization / supply-chain
- Applies to: `backend/ml/aasist_model.py` (`torch.load(model_path, ...)`)
- Check: model path is never attacker-controllable; prefer `weights_only=True`; verify checkpoint integrity.
- Status: ACTIVE
- First seen: 2026-06-23 · Last reviewed: 2026-06-23
- Notes: loads a local trusted `.pth` today; risk rises if `MODEL_PATH` becomes env/user-driven.

### T-002 Untrusted audio decoding (DoS / decoder crash)
- Category: DoS / untrusted input
- Applies to: `backend/ml/audio_utils.py`, `POST /api/analyze`
- Check: size cap enforced (`MAX_UPLOAD_BYTES`); decompression-bomb and malformed-file handling; CPU/RAM ceiling per request.
- Status: ACTIVE
- First seen: 2026-06-23 · Last reviewed: 2026-06-23
- Notes: 25 MB cap exists; no duration/CPU cap, no decode timeout.

### T-003 Unauthenticated WebSocket, no rate limit
- Category: DoS / authn
- Applies to: `backend/app/routes/websocket.py` (`/ws/analyze`)
- Check: per-connection resource caps, max message size, connection rate limit, auth/origin check.
- Status: ACTIVE
- First seen: 2026-06-23 · Last reviewed: 2026-06-23
- Notes: accepts raw PCM from anyone; buffer growth bounded only by client behaviour.

### T-004 Permissive CORS
- Category: authn / web
- Applies to: `backend/app/main.py` (`allow_origins=["*"]`)
- Check: becomes dangerous if credentials/cookies are ever added; lock to known origins before prod.
- Status: ACCEPTED
- First seen: 2026-06-23 · Last reviewed: 2026-06-23
- Notes: deliberate for the demo (no auth/cookies yet). Re-classify to ACTIVE when auth lands.

### T-005 No authentication on any endpoint
- Category: authn/authz
- Applies to: all of `backend/app/`
- Check: any deployment beyond a local demo needs authn + per-tenant authz.
- Status: ACTIVE
- First seen: 2026-06-23 · Last reviewed: 2026-06-23

### T-006 Dependency CVEs (backend + frontend)
- Category: supply-chain
- Applies to: `backend/requirements.txt`, `frontend/package.json`
- Check: each run, look up CVEs for the **pinned** versions (torch, librosa, fastapi, pydantic; tanstack, recharts, vite). Run `npm audit --omit=dev` when installable.
- Status: ACTIVE
- First seen: 2026-06-23 · Last reviewed: 2026-06-23
- Notes: this is the entry most likely to surface *new* risks over time.

### T-007 No TLS / exposed Redis in compose
- Category: infra / transport
- Applies to: `docker-compose.yml`
- Check: TLS termination, Redis not published to host, containers not running as root, no `:latest` drift.
- Status: ACTIVE
- First seen: 2026-06-23 · Last reviewed: 2026-06-23

### T-008 Secrets / client-side leakage
- Category: secrets
- Applies to: `frontend/` (`VITE_*` inlined into the bundle), tracked files, logs
- Check: no API keys/tokens in tracked files or the client bundle; `getUserMedia` consent; no sensitive data logged.
- Status: ACTIVE
- First seen: 2026-06-23 · Last reviewed: 2026-06-23
