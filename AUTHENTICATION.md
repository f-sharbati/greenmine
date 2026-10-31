# Registration, email activation and two-step login

This implements the supplied registration/login flowchart in the shared Next.js/Python application. The existing Android WebView shell consumes the same endpoints and screens.

## Flow

**Registration:** email + password + password confirmation + CAPTCHA -> server validation -> salted password KDF -> inactive account -> email OTP -> successful code confirmation -> active account -> sign-in screen. Activation does not create a dashboard session.

**Login:** email + password -> account lookup/password validation -> inactive accounts are directed into activation -> active accounts receive a login OTP -> correct code -> authenticated HttpOnly session -> dashboard. Login has no extra image CAPTCHA; registration does. Incorrect passwords are rejected and recorded without sending a login email.

## Passwords and transport

New/reset passwords use **PBKDF2-HMAC-SHA-256 with 600,000 iterations**, a random 16-byte per-password salt and a 32-byte derived key. Hashes carry an algorithm/version prefix. Existing scrypt hashes remain verifiable and upgrade after a correct password check; user IDs, workspaces and CSV data are retained. SHA-256 is a hash function, not a network protocol; passwords are never stored as a fast, unsalted SHA-256 digest or replaced by a reusable client-side hash.

Production requires `APP_ORIGIN=https://greenmineapp.ir`, secure HttpOnly SameSite=Lax cookies and HTTPS at the reverse proxy. SMTP uses authenticated STARTTLS on port 587 or implicit TLS on port 465 with certificate verification. Existing sessions remain valid until expiry/logout; new sessions require the login code. Existing accounts migrate as active to preserve established accounts; their next new login still requires mailbox verification. New accounts always start inactive.

Reference: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html . Email verification follows the requested product flow; this is not a claim of phishing-resistant authentication or NIST assurance certification.

## CAPTCHA and email-code controls

- Registration uses a basic self-hosted six-digit raster-image CAPTCHA, validated on the server, bound to the browser, valid for five minutes, and consumed once. The answer is not returned as text/markup. Refresh invalidates that browser's prior CAPTCHA. This is a basic friction/rate-control measure, not a guarantee against automated image recognition.
- Email codes are six digits, valid once for ten minutes, with at most five incorrect attempts per challenge. Persian and Arabic digits normalize before verification.
- Codes are HMAC-SHA-256 hashed with a private server key and purpose/browser/challenge binding. Plaintext codes are not stored in SQLite or returned through the API.
- Resending waits at least 60 seconds, rotates the challenge/code, and invalidates the old challenge. Delivery is limited per account and client. Expired/used/failed challenges cannot issue sessions.
- Account activation and login purposes are distinct. An activation code never becomes a login session. Password recovery invalidates pending authentication challenges and prior sessions.
- A password-hash fingerprint prevents a pending login code from surviving a password change. Atomic transactions ensure concurrent redemption succeeds once.
- `auth_events` records password rejection, OTP rejection, activation and verified login without passwords or codes. Email/client identifiers are hashed; events expire after 30 days. Existing account/client rate limits remain enforced.
- SMTP failure leaves no usable verification challenge and never grants a session. A registration whose mail delivery failed remains inactive; signing in with the same credentials offers activation again.

The service adds `users.active`, `captcha_challenges`, `auth_challenges`, and `auth_events` through additive schema changes. Session-token digests continue to use SHA-256. The private HMAC key is stored under `GREENMINE_DATA_DIR` as `recovery.key`; retain it with the private data volume and do not package it into source archives.

## Required mail bootstrap before rollout

Keep the supplied settings:

```dotenv
APP_ORIGIN=https://greenmineapp.ir
GREENMINE_DATA_DIR=/data
GREENMINE_PYTHON_ROOT=/opt/greenmine/python
PYTHON_EXECUTABLE=/opt/venv/bin/python
GREENMINE_ADMIN_EMAIL=fazi.sharbati@gmail.com
SMTP_REQUIRE_SETUP=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_TLS=starttls
SMTP_USER=mehrava.sharbati@gmail.com
SMTP_FROM=mehrava.sharbati@gmail.com
SMTP_PASSWORD=
```

`SMTP_REQUIRE_SETUP=1` deliberately ignores SMTP environment defaults until private `/data/mail.json` has been freshly configured. A blank `SMTP_PASSWORD` cannot send activation/login codes. Configure mail **before restarting this auth release**, to avoid making new sign-ins unavailable.

From the application root, as the same OS user that runs GreenMine:

```bash
export GREENMINE_DATA_DIR=/data
export GREENMINE_ADMIN_EMAIL=fazi.sharbati@gmail.com
/opt/venv/bin/python server/configure_mail.py
```

Enter `smtp.gmail.com`, sender `mehrava.sharbati@gmail.com`, a fresh Gmail app password at the hidden prompt, and port `587`. This command verifies SMTP authentication and writes private `/data/mail.json` with mode 600. It sends no email and prints no password. It does not require an existing login, solving the bootstrap dependency. After login, the project administrator can update the same settings through Email settings.

If `/opt/greenmine/config/mail.env` has already been updated privately with the fresh app password, retain mode 600, load it into the operator process without printing it, and run `server/configure_mail.py --from-env` instead. That file is not modified by the application or included in the ZIP. Keep `SMTP_REQUIRE_SETUP=1`; do not bypass setup by changing it to zero.

No real SMTP password was provided in this task. Real Gmail delivery remains a server setup/acceptance step. Tests use mocked SMTP and isolated temporary databases, and never send codes to actual users.

## API and verification

`GET /api/auth?action=context` creates a browser-bound HttpOnly pending-auth context. `GET /api/auth?action=captcha` additionally provides the registration image. `POST /api/auth` accepts `register`, `login`, `auth_verify`, `auth_resend`, `forgot`, `reset`, and `logout`. Intermediate responses contain stage/challenge/timing data, never a session token. Only successful login-code verification sets the authenticated session cookie. Origin checks apply to state-changing requests.

Backend tests cover the complete flow, old-schema migration, legacy hash upgrade, attempts/expiry, resends, browser binding, cross-account isolation, concurrent use, SMTP errors, password changes, and recovery. Existing backend fixtures use test-only mocks to complete verification; there is no runtime bypass flag or production test-code endpoint.

The Android instrumentation defaults to the new auth UI smoke path. Full OTP delivery requires configured SMTP and an operator-controlled test mailbox; it is not silently bypassed by the old password-only registration harness.

## Operator-selected temporary password mode

The owner authorized email-and-password access while fresh SMTP is being prepared. Set GREENMINE_AUTH_MODE=password explicitly to use this temporary mode. New signups still validate the CAPTCHA and matching passwords, use the same versioned PBKDF2 KDF, start empty and active, and receive an authenticated session. Existing inactive accounts are not silently activated. Rate limits, browser context, HTTPS, cookie controls and ownership checks remain enforced.

The default is GREENMINE_AUTH_MODE=email_otp. An absent or failing mail service never changes that mode or grants a password-only session. Once fresh SMTP is configured and authenticated, restart the same image with GREENMINE_AUTH_MODE=email_otp and verify live email delivery. Existing sessions and data are retained. Email recovery still requires configured SMTP in either mode. There is no date-based switch or client-controlled authentication override.
