# GROWWW INVESTOR DISCOVERY ENGINE – DOMAIN, HTTPS & ACCESS MODE GUIDE
**Document Version:** 1.0  
**Phase:** 8 Production Architecture  

---

## 1. ACCESS MODES

The Growww Discovery Engine supports two distinct production access modes:

### Mode 1: Private Deployment (Default & Recommended)
- **Configuration:** `REQUIRE_AUTH=true`, `ENABLE_DEMO_MODE=false`
- **Behavior:**
  - Entire application is gated behind the PBKDF2 authentication portal.
  - Access is restricted to 4 authenticated roles: `ADMIN`, `RESEARCHER`, `VIEWER`, `AUDITOR`.
  - Sessions automatically expire after 120 minutes of inactivity (`AUTH_SESSION_TIMEOUT_MINUTES=120`).
  - Raw CSV downloads and manual pipeline triggers require `ADMIN` or `RESEARCHER` permissions.

### Mode 2: Restricted Public Demo Mode (Optional Stakeholder Preview)
- **Configuration:** `ENABLE_DEMO_MODE=true`
- **Safeguards Enforced:**
  1. Default access is forced to `VIEWER` (read-only overview, opportunity radar, digests).
  2. Synthetic demo reviews remain strictly quarantined (`SYNTHETIC_DEMO`), completely excluded from metrics.
  3. All review quotes and text are processed through automated PII neutralization before rendering.
  4. Ingestion triggers, Source Manager modification, schema migrations, and raw review downloads are completely hidden from the UI.
  5. PDF and CSV exports carry a clear `DEMO RESEARCH WATERMARK`.

---

## 2. PRODUCTION REVERSE PROXY & HTTPS (TLS) CONFIGURATION

Streamlit does not terminate TLS natively in high-concurrency environments. A production reverse proxy (Nginx or Caddy) must be placed in front of port 8501.

### Option A: Nginx Reverse Proxy Configuration (`/etc/nginx/sites-available/growww.conf`)

```nginx
# HTTP -> HTTPS Redirect
server {
    listen 80;
    listen [::]:80;
    server_name discovery.growww-research.internal;
    return 301 https://$host$request_uri;
}

# Production TLS Virtual Host
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name discovery.growww-research.internal;

    # SSL Certificates (Let's Encrypt or Corporate Internal PKI)
    ssl_certificate /etc/letsencrypt/live/discovery.growww-research.internal/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/discovery.growww-research.internal/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Hardening Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: data:;" always;

    # Streamlit Reverse Proxy & WebSocket Pass-Through
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400; # Prevent WebSocket dropouts
    }

    # Health Check Endpoint Pass-Through
    location /_stcore/health {
        proxy_pass http://127.0.0.1:8501/_stcore/health;
        access_log off;
    }
}
```

### Option B: Caddy Reverse Proxy Configuration (`Caddyfile`)

Caddy automatically provisions and renews TLS certificates via Let's Encrypt:

```caddy
discovery.growww-research.internal {
    encode gzip zstd

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
    }

    reverse_proxy 127.0.0.1:8501 {
        header_up Host {host}
        header_up X-Real-IP {remote}
    }
}
```

---

## 3. STREAMLIT CONFIGURATION AUDIT

Ensure `.streamlit/config.toml` includes:

```toml
[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
```
