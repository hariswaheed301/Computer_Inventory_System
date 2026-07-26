# Plan: Secure Your Authentication System

## TL;DR

The issue: **credentials appear plain-text in the Network tab because you're testing on HTTP (localhost) instead of HTTPS**. This is expected for HTTP but completely avoidable. The solution involves: (1) enforcing HTTPS locally, (2) adding security headers to prevent attacks, (3) implementing rate limiting to block brute force, and (4) validating passwords properly.

---

## Current State

- ✅ Password hashing with Werkzeug (good)
- ✅ CSRF protection enabled
- ✅ Session management with Flask-Login
- ✅ SSL/TLS config in production (Render.com)
- ❌ **Plain text credentials in POST request payload**
- ❌ **No HTTPS enforcement on localhost**
- ❌ No rate limiting on login attempts
- ❌ No password complexity requirements
- ❌ No account lockout mechanism
- ❌ Browser autocomplete on password fields
- ❌ Missing security headers (CSP, X-Frame-Options, etc.)

## Root Cause

When testing on localhost without HTTPS, credentials are transmitted over HTTP unencrypted. The POST payload contains identifier, password, csrf_token in plain text. This is visible in Network tab.

---

## Implementation Steps

### Phase 1: Critical Security (must do before demo)

#### 1. Enforce HTTPS in Production & Local

- Add `Strict-Transport-Security` header to force HTTPS
- Configure `PREFERRED_URL_SCHEME = 'https'` in production config
- Run local development with self-signed HTTPS certificate
- Redirect all HTTP requests to HTTPS

**File:** `app/config.py`

#### 2. Add Security Headers to All Responses

Prevent XSS, clickjacking, MIME sniffing:

- `Content-Security-Policy: default-src 'self'; script-src 'self' cdn.jsdelivr.net use.fontawesome.com; style-src 'self' cdn.jsdelivr.net`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `X-XSS-Protection: 1; mode=block`

**File:** `app/__init__.py` (add after_request middleware)

#### 3. Implement Rate Limiting on Login Endpoint

- Max 5 login attempts per IP per 15 minutes
- Returns 429 error if exceeded
- Prevents brute force attacks

**Dependency:** `flask-limiter`
**Files:** `app/security.py` (new), `app/routes/auth_routes.py` (add decorator)

#### 4. Fix Browser Autocomplete Issues

- Add `autocomplete="off"` to password fields
- Add `autocomplete="username"` to identifier field
- Prevent browser from saving and auto-filling credentials

**File:** `app/templates/auth/login.html`

---

### Phase 2: Enhanced Validation (Recommended)

#### 5. Add Password Complexity Requirements

- Minimum 8 characters
- At least 1 uppercase letter (A-Z)
- At least 1 lowercase letter (a-z)
- At least 1 number (0-9)
- At least 1 special character (!@#$%^&\*)
- Reject common passwords (top 10k list)

**File:** `app/security.py` (new validation function), `app/models/users.py` (update create method)

#### 6. Implement Account Lockout

- Track failed login attempts per user in database
- Lock account after 5 failed attempts
- Auto-unlock after 30 minutes OR admin unlock
- Notify user on suspicious activity

**Files:** `app/models/users.py`, `app/routes/auth_routes.py`, database migration

#### 7. Input Validation & Sanitization

- Validate email format using regex or email-validator
- Sanitize inputs to prevent injection attacks
- Add field length limits (username max 50, email max 100)
- Trim whitespace from inputs

**File:** `app/security.py` (validation helpers)

#### 8. Security Logging

- Log all authentication events (success/failure/lockout)
- Track IP addresses and user agents
- Alert on suspicious patterns (multiple failures)
- Store logs in database for audit trail

**Files:** `app/models/users.py`, `app/routes/auth_routes.py`

---

### Phase 3: Optional Advanced (Nice-to-Have)

#### 9. Implement 2FA with TOTP

- Google Authenticator / Authy support
- QR code generation for setup
- Backup codes for account recovery

#### 10. Session Security Improvements

- Shorter session timeout (15 minutes of inactivity)
- Session invalidation on logout
- Prevent session fixation attacks
- Bind session to IP/user agent (detect hijacking)

#### 11. Anomaly Detection

- Track login locations and times
- Alert if login from unusual IP
- Require verification email on suspicious logins

---

## Relevant Files to Modify

### Core Files

- **`app/config.py`** — Add security headers, HTTPS enforcement, rate limit config
- **`app/routes/auth_routes.py`** — Add rate limiting, account lockout, logging, validation
- **`app/models/users.py`** — Add failed attempt tracking, account lock status, validation
- **`app/templates/auth/login.html`** — Disable autocomplete, add security attributes
- **`app/__init__.py`** — Register rate limiting middleware, security headers middleware

### New Files to Create

- **`app/security.py`** — Rate limiting decorator, password validation, input sanitization
- **`app/models/audit_log.py`** (optional) — Track auth events for compliance

### Configuration

- **`requirements.txt`** — Add `flask-limiter` dependency

---

## Security Headers Explanation

| Header                        | Purpose                                     | Value                                                    |
| ----------------------------- | ------------------------------------------- | -------------------------------------------------------- |
| **Strict-Transport-Security** | Force HTTPS                                 | `max-age=31536000; includeSubDomains`                    |
| **Content-Security-Policy**   | Prevent XSS, script injection               | `default-src 'self'; script-src 'self' cdn.jsdelivr.net` |
| **X-Frame-Options**           | Prevent clickjacking (iframe attacks)       | `DENY`                                                   |
| **X-Content-Type-Options**    | Prevent MIME sniffing                       | `nosniff`                                                |
| **Referrer-Policy**           | Control referrer leakage                    | `strict-origin-when-cross-origin`                        |
| **X-XSS-Protection**          | Legacy XSS filter (modern browsers use CSP) | `1; mode=block`                                          |

---

## Rate Limiting Strategy

```
Endpoint               Limit                 Window    Effect
/login                5 attempts per IP     15 min    Returns 429 Too Many Requests
/register (admin)     3 attempts per IP     1 hour    Returns 429 Too Many Requests
/api/users            10 requests per user  1 minute  Returns 429 Too Many Requests
```

**Backend Choice:** In-memory cache for MVP (sufficient for single-server), Redis for production scale.

---

## Account Lockout Strategy

| Metric                          | Value             |
| ------------------------------- | ----------------- |
| **Failed attempts before lock** | 5                 |
| **Lockout duration**            | 30 minutes        |
| **Auto-unlock**                 | Yes, after 30 min |
| **Manual unlock**               | ADMIN only        |
| **Email notification**          | Yes, on lockout   |
| **Clear counter on success**    | Yes               |

---

## Database Changes Required

### Add to `users` table

```sql
ALTER TABLE users ADD COLUMN failed_login_attempts INT DEFAULT 0;
ALTER TABLE users ADD COLUMN is_locked BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN locked_until TIMESTAMP;
ALTER TABLE users ADD COLUMN last_login_attempt TIMESTAMP;
ALTER TABLE users ADD COLUMN last_login_ip VARCHAR(45);
```

### New `login_audit_log` table (optional)

```sql
CREATE TABLE login_audit_log (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    attempt_type VARCHAR(20), -- 'success', 'failure', 'lockout'
    ip_address VARCHAR(45),
    user_agent TEXT,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    failure_reason VARCHAR(100)
);
```

---

## Verification Checklist

- [ ] **HTTPS Local:** Run app with self-signed cert, credentials encrypted in transit
- [ ] **Rate Limiting:** Attempt 6 logins → 6th rejected with 429 error
- [ ] **Security Headers:** `curl -i http://localhost:5000/login` shows all required headers
- [ ] **Production HTTPS:** Render.com redirects HTTP → HTTPS automatically
- [ ] **Password Complexity:** Weak password rejected during registration
- [ ] **Account Lockout:** 5 failed attempts → account locked, message shown
- [ ] **Autocomplete Off:** Browser doesn't suggest saved passwords
- [ ] **Audit Logs:** All login events (success/failure/lockout) recorded in database
- [ ] **CSP Enforcement:** External scripts only from whitelisted domains
- [ ] **Session Security:** Session cookie has `HttpOnly`, `Secure`, `SameSite=Lax` flags

---

## Why Credentials Show in Network Tab (Technical Explanation)

### HTTP (Current on localhost)

```
POST /login HTTP/1.1
Content-Type: application/x-www-form-urlencoded

identifier=admin&password=admin123&csrf_token=abc123
```

❌ **Plain text transmission** — anyone on network sees it
❌ **No encryption** — visible in Network tab, sniffable on WiFi

### HTTPS (After fix)

```
POST /login HTTP/1.1  [Actually: TLS 1.3 encrypted connection]
Content-Type: application/x-www-form-urlencoded

[ENCRYPTED BINARY DATA - Cannot be read without private key]
```

✅ **Encrypted in transit** — only endpoint can decrypt
✅ **Network tab shows REQUEST** but actual transmission is encrypted
✅ **Industry standard** — same as banks, Gmail, AWS, etc.

---

## Key Decisions Made

- ✅ **HTTPS over HTTP:** Use self-signed cert locally (`ssl_context=('adhoc')` in Flask or werkzeug)
- ✅ **Rate Limiting Backend:** In-memory cache sufficient for MVP, upgrade to Redis later
- ✅ **Password Requirements:** Industry standard (8+ chars, mixed case, numbers, symbols)
- ⏭️ **2FA/MFA:** Skip for MVP Phase 1, add in Phase 2 if time permits
- ✅ **Account Lockout:** 5 attempts → 30 min lock (balances security with user experience)
- ✅ **Logging:** Database-backed audit trail for compliance and debugging

---

## Timeline Estimate

| Phase       | Tasks                                       | Estimated Time | Priority    |
| ----------- | ------------------------------------------- | -------------- | ----------- |
| **Phase 1** | HTTPS + Headers + Rate Limit + Autocomplete | 2-3 hours      | 🔴 CRITICAL |
| **Phase 2** | Password Validation + Lockout + Logging     | 2-3 hours      | 🟠 HIGH     |
| **Phase 3** | 2FA + Advanced Features                     | 4-5 hours      | 🟡 OPTIONAL |

---

## Quick Start Commands

```bash
# Install dependencies
pip install flask-limiter

# Test HTTPS locally (requires pyopenssl)
pip install pyopenssl

# Run with HTTPS
python wsgi.py --ssl-context=adhoc

# Test rate limiting
for i in {1..10}; do curl -X POST http://localhost:5000/login -d "identifier=admin&password=wrong"; done

# Verify security headers
curl -i http://localhost:5000/login | grep -E "Strict-Transport|X-Frame|Content-Security"
```

---

## Questions Before Implementation

1. **2FA Required?** Skip for MVP or implement as Phase 1 stretch goal?
2. **Email Notifications?** Send alerts on failed attempts / account lockout?
3. **IP Whitelisting?** Trust certain IPs to skip rate limiting?
4. **Password Expiration?** Force password change every 90 days (optional)?
5. **SSO/OAuth?** Add Google/GitHub login as alternative (Phase 3)?

---

## Reference Links

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [Flask-Limiter Documentation](https://flask-limiter.readthedocs.io/)
- [Werkzeug Security Functions](https://werkzeug.palletsprojects.com/en/2.3.x/security/)
