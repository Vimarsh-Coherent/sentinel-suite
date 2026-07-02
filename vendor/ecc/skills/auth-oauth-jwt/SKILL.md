---
name: auth-oauth-jwt
description: Implement secure login, sessions, tokens, and permissions (OAuth2, OpenID Connect, JWT, sessions, RBAC). Use for auth, login, sign in, OAuth, JWT, tokens, sessions, permissions, roles, access control.
---

# Authentication & Authorization

## When to use
Anything about who the user is and what they can do. Keywords: auth, login, OAuth, JWT, token, session, RBAC, permission.

## Authentication (who you are)
- Prefer **OAuth2 / OpenID Connect** with a trusted provider over rolling your own.
- **Sessions** (server-side, httpOnly cookie) for web apps; **JWT** for stateless APIs.
- Hash passwords with **bcrypt/argon2** (never plain/​MD5/SHA). Add MFA where possible.

## Authorization (what you can do)
- **RBAC** (roles) for most apps; ABAC for fine-grained. Check on the **server**, every request.

## Token hygiene
- Short-lived access tokens + refresh tokens. - Validate signature, expiry, audience, issuer. - Store tokens in httpOnly cookies, not localStorage. - Revoke on logout.

## Pitfalls
- Trusting client-side checks. - Long-lived JWTs with no revocation. - Secrets/keys in the repo. - Not rotating keys.
