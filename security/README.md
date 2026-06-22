# Security watchdog

A self-maintaining security layer for Dhwani-Kavach, built from three pieces:

1. **`.claude/agents/security-sentinel.md`** — a read-only specialist agent (the "who").
2. **`security/THREAT-LIBRARY.md`** — its persistent memory; grows every run (the "learning").
3. **A scheduled cloud routine** — runs the agent daily, unattended (the "constantly").

## How the "self-learning" actually works

There is no weight-level self-training. Continuity comes from two grounded mechanisms:

- **Memory across runs** — the agent reads `THREAT-LIBRARY.md` first, re-checks every known
  risk for regressions, and appends newly-discovered risk classes.
- **Intel refresh each run** — it WebSearches new CVEs for the *pinned* dependency versions
  and new attack techniques for the stack (FastAPI, PyTorch model loading, audio decoders,
  WebSocket DoS, voice-biometric evasion). That's how risks discovered "years from now" get
  caught: the catalog and the model stay current, the audit re-runs against today's reality.

## Self-update — gated, never autonomous

The agent can **propose** edits to its own brief and threat library via a human-reviewed PR
(`security/threat-library-<date>`). It can **never** auto-merge, edit product code, or change
CI/permissions. This is deliberate: an unattended agent that could silently rewrite its own
security rules — or hold write access to production — would be a bigger risk than the ones it
hunts. Least privilege, read-only on code, human in the loop for every change.

## Deploying into a customer workspace (e.g. UCO Bank)

The same agent guards a customer's *integration*, not just the core product. One routine per
tenant:

1. Point a scheduled routine (see the `schedule` skill) at the customer's integration repo.
2. Give it that tenant's own Anthropic API key (scoped, least-privilege) and **read-only**
   repo access — an audit never needs production write.
3. Seed a tenant `THREAT-LIBRARY.md` in their repo; the agent extends the core surface with
   their integration specifics (how they call the API, TLS termination, key storage, network
   exposure, which product version they pin).
4. Findings land in *their* tracker. Their library grows independently of ours.

## Honest limits

- "Safe forever" is not a guarantee anything can make. This raises the floor — continuous
  re-audit against current code + fresh threat intel — it does not certify the product secure.
- The agent finds and reports; humans triage and fix. Critical findings still need people.
- API keys it's given should be least-privilege and rotatable; never hand it production
  credentials or merge rights.
