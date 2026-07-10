# Security Policy

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, email ** 70114@cch.edu.pk **  with:

- A description of the vulnerability and its potential impact
- Steps to reproduce (a minimal repro is ideal)
- Any suggested fix, if you have one

You should expect an initial response within a few days. Once a fix is available, we'll credit you
in the release notes unless you'd prefer to stay anonymous.

## Supported versions

This project is under active development on a single `main` branch — only the latest commit is
supported.

## What's already covered

A non-exhaustive list of the security measures already in place, for context before you report
something that may already be handled:

- **Local-directory analysis** is restricted by a blocklist against system directories
  (`/etc`, `/Users`, `/System`, `/root`, etc. — see `app/analysis/ingestion.py`), preventing
  arbitrary filesystem disclosure via the `/analyze/local` endpoint.
- **GitHub URLs** are validated to actually be `github.com` before use (`app/analysis/github.py`).
- **LLM-generated markdown** (explanations, plans) is sanitized with DOMPurify before rendering,
  since it's derived from analyzing arbitrary — potentially adversarial — source code.
- **Passwords** are bcrypt-hashed; **JWTs** are short-lived and signed with `JWT_SECRET_KEY`.
- **Every analysis record** is access-controlled per-user (`user_id` ownership check).
- **Rate limiting** via `slowapi`, with an optional Cloudflare Turnstile challenge on registration.
- Quota consumption is atomic at submission time (no double-spend via concurrent requests).

If you find a gap in any of the above, that's exactly the kind of report this policy is for.
