# TalentAI — Production Deployment & Operations Guide

## 1. System Architecture Overview

TalentAI is deployed with a unified-origin architecture designed for security, performance, and isolated internal communication:

```
                          [ Public HTTPS Requests ]
                                      │
                                      ▼
             ┌──────────────────────────────────────────────────┐
             │                Nginx Reverse Proxy               │
             │           (Port 80 HTTP -> 443 HTTPS)            │
             │  - SSL/TLS Termination (TLS 1.2/1.3)             │
             │  - Serves React SPA (Static Assets)              │
             │  - Proxies Backend APIs to Internal Network      │
             │  - Strict TLS Pre-Flight Verification Entrypoint │
             └────────┬────────────────────────────────┬────────┘
                      │                                │
      [ /assets/*, /, SPA Routes ]             [ /auth, /upload, /matching, ... ]
                      │                                │
                      ▼                                ▼
             ┌─────────────────┐             ┌─────────────────────────┐
             │ React SPA Build │             │     FastAPI Backend     │
             │ (Static Bundle) │             │ (Internal Port 8000)    │
             └─────────────────┘             └────────────┬────────────┘
                                                          │
                                     ┌────────────────────┴────────────────────┐
                                     │                                         │
                                     ▼                                         ▼
                          ┌─────────────────────┐                   ┌─────────────────────┐
                          │   MongoDB 7.0       │                   │    Ollama Engine    │
                          │ (Internal: 27017)   │                   │  (Host or Isolated) │
                          │ Persistent Volumes  │                   │ Auto-Lifecycle Mgr  │
                          └─────────────────────┘                   └─────────────────────┘
```

### Key Architectural Safeguards
1. **Single Unified HTTPS Origin:** Nginx terminates SSL/TLS and routes both the React UI and API endpoints (`/auth/`, `/upload/`, `/batches/`, `/job-description/`, `/matching/`, `/ranking/`, `/status/`, `/results/`, `/demo/`, `/queue/`, `/health`) through the same public origin. Cookies use `SameSite=Lax` and `Secure=True`.
2. **Shielded Internal Network:** FastAPI and MongoDB run exclusively on the isolated `talentai_internal` Docker network. Neither port 8000 nor port 27017 is published to the public host interface.
3. **On-Demand AI Lifecycle Manager:** The dedicated Python service (`AILifecycleManager`) manages local LLM interactions, tracks active/queued jobs, cancels idle shutdown when work arrives, enforces a 5-minute idle grace period, and **never interrupts or terminates an external/shared Ollama process it did not spawn**.
4. **Interactive HR Account Provisioning:** No default credentials exist in configuration, images, or environment variables. Initial and subsequent HR accounts are provisioned exclusively through an interactive CLI with password confirmation and minimum 8-character validation.

---

## 2. Host Prerequisites & Linux Host Networking for Ollama

### System Prerequisites
- **Operating System:** Ubuntu 22.04 LTS / Debian 12 / RHEL 9 (or compatible Linux distribution)
- **Docker Engine:** Version 24.0 or later
- **Docker Compose:** Version 2.20 or later
- **Ollama:** Installed on the host with the `qwen3:8b` model pulled:
  ```bash
  ollama pull qwen3:8b
  ```
- **Domain & DNS:** Fully qualified domain name (e.g., `talentai.company.com`) resolving to the host's public IP.
- **Valid Production TLS Certificates:** `talentai.crt` (full chain) and `talentai.key` (private key).

### Linux Host Networking & Firewall Hardening (Ollama)

When running Ollama directly on a Linux host (e.g., for direct GPU acceleration with CUDA/ROCm):

1. **Host Gateway Mapping:**
   Docker on Linux does not resolve `host.docker.internal` by default. [docker-compose.yml](docker-compose.yml) explicitly includes:
   ```yaml
   extra_hosts:
     - "host.docker.internal:host-gateway"
   ```
   This routes container requests for `host.docker.internal` to the Docker bridge gateway interface (typically `172.17.0.1`).

2. **Ollama Service Binding on Host:**
   By default, Ollama binds only to loopback (`127.0.0.1:11434`), which refuses connections from Docker bridge interfaces. Configure Ollama to listen across interfaces:
   ```bash
   sudo systemctl edit ollama.service
   ```
   Add the following override lines:
   ```ini
   [Service]
   Environment="OLLAMA_HOST=0.0.0.0:11434"
   ```
   Save the file and restart Ollama:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart ollama
   ```

3. **Firewall Protection (DO NOT EXPOSE OLLAMA PUBLICLY):**
   Restrict port 11434 to local Docker bridge subnets and the host itself so external attackers cannot access your LLM:
   ```bash
   # Using UFW (Uncomplicated Firewall):
   sudo ufw allow in on docker0 to any port 11434 proto tcp
   sudo ufw allow from 127.0.0.1 to any port 11434 proto tcp
   sudo ufw allow from 172.16.0.0/12 to any port 11434 proto tcp
   sudo ufw deny 11434/tcp
   sudo ufw reload
   ```
   Verify that Ollama responds from the host:
   ```bash
   curl http://127.0.0.1:11434/api/version
   # Expected output: {"version":"..."}
   ```

4. **Shared Host Ollama Non-Interference Guarantee:**
   When connecting to an existing host Ollama service, `AILifecycleManager` records `_subprocess = None`. Its idle shutdown worker and termination handlers explicitly verify `if self._subprocess and self._subprocess.returncode is None:`. Consequently, `AILifecycleManager` will **never** stop, kill, or signal the host's shared Ollama process.

---

## 3. Pre-Flight TLS Certificate Requirements

TalentAI enforces strict production HTTPS. The Nginx edge container includes an automated pre-flight entrypoint (`nginx-entrypoint.sh`) that verifies certificates before starting:

- If valid certificates are present in `/etc/nginx/ssl/`, Nginx validates configuration syntax and starts normally.
- If certificates are missing or zero bytes, the container **fails immediately with exit code 1** and logs a clear diagnostic error. It refuses to fall back to unencrypted HTTP or self-signed placeholders in production.

### Step 3.1: Certificate Placement
Before launching the Docker stack, copy your valid production certificates to the host directory:
```bash
cp /path/to/fullchain.pem ./nginx/ssl/talentai.crt
cp /path/to/privkey.pem ./nginx/ssl/talentai.key
```
Enforce strict read-only permissions on the private key:
```bash
chmod 644 ./nginx/ssl/talentai.crt
chmod 600 ./nginx/ssl/talentai.key
```

---

## 4. Step-by-Step Deployment Instructions

### Step 4.1: Populate Environment Variables
Copy the production environment template:
```bash
cp .env.example .env
```
Generate a cryptographically secure 64-character secret key:
```bash
openssl rand -hex 32
```
Edit `.env` and configure:
```ini
ENVIRONMENT=production
SECRET_KEY=<INSERT_GENERATED_64_CHAR_KEY>
ALLOWED_ORIGINS=https://talentai.yourdomain.com

MONGO_INITDB_ROOT_USERNAME=talentai_admin
MONGO_INITDB_ROOT_PASSWORD=<INSERT_STRONG_GENERATED_DATABASE_PASSWORD>
MONGODB_URI=mongodb://talentai_admin:<INSERT_STRONG_GENERATED_DATABASE_PASSWORD>@mongodb:27017/talentai?authSource=admin
MONGODB_DATABASE=talentai

OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_AUTO_LIFECYCLE=true
```

### Step 4.2: Build and Launch Containers
Build production images with build-context protection (enforced by `.dockerignore`):
```bash
docker compose build --no-cache
docker compose up -d
```

Verify service status and health checks:
```bash
docker compose ps
```
Expected output:
```
NAME                IMAGE               COMMAND                  SERVICE             STATUS
talentai_mongodb    mongo:7.0           "docker-entrypoint.s…"   mongodb             Up (healthy)
talentai_backend    talentai-backend    "uvicorn main:app --…"   backend             Up (healthy)
talentai_nginx      talentai-nginx      "/docker-entrypoint-…"   nginx               Up (healthy)
```

Check backend application logs:
```bash
docker compose logs -f backend
```

---

## 5. Provision Initial HR Account (Interactive CLI)

TalentAI does not seed default credentials or accept passwords via environment variables. An authorized administrator must provision the initial HR team member through the interactive CLI inside the running backend container:

```bash
docker compose exec -it backend python -m app.cli.manage_hr create --username hr_lead --email hr@company.com --name "HR Team Lead"
```

You will be prompted interactively for a secure password (minimum 8 characters) with confirmation:
```
Enter password for HR user 'hr_lead' (min 8 chars): ********
Confirm password: ********
Successfully created HR user: hr_lead (HR Team Lead)
```
> **Security Audit Guarantee:** Passwords entered via `getpass` are never echoed, never stored in shell history (`~/.bash_history`), never visible in process tables (`ps aux`), and never recorded in application logs.

### Additional HR Management Commands
- **List authorized HR accounts:**
  ```bash
  docker compose exec backend python -m app.cli.manage_hr list
  ```
- **Reset an HR user's password (clears all active sessions):**
  ```bash
  docker compose exec -it backend python -m app.cli.manage_hr reset-password --username hr_lead
  ```

---

## 6. Host-Managed TLS Certificate Renewal & Zero-Downtime Reload

Because Nginx terminates TLS inside Docker while certificates are renewed on the host (e.g., via Let's Encrypt / Certbot), follow this deterministic renewal procedure:

### 6.1: Automated Host Renewal Command
Configure a host cron job or systemd timer (`/etc/cron.daily/talentai-cert-renew`):
```bash
#!/bin/bash
set -e

DOMAIN="talentai.yourdomain.com"
APP_DIR="/opt/talentai"

# 1. Run Certbot renewal on host
certbot renew --quiet

# 2. Copy updated certificates to the application SSL directory
cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem ${APP_DIR}/nginx/ssl/talentai.crt
cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem ${APP_DIR}/nginx/ssl/talentai.key
chmod 644 ${APP_DIR}/nginx/ssl/talentai.crt
chmod 600 ${APP_DIR}/nginx/ssl/talentai.key

# 3. Validate Nginx configuration syntax inside container
docker compose -f ${APP_DIR}/docker-compose.yml exec -T nginx nginx -t

# 4. Reload Nginx without dropping active client connections
docker compose -f ${APP_DIR}/docker-compose.yml exec -T nginx nginx -s reload
```
Make the script executable:
```bash
chmod +x /etc/cron.daily/talentai-cert-renew
```

### 6.2: Renewal Failure Recovery
- `nginx -t` tests the renewed certificate files before executing `nginx -s reload`.
- If an invalid or corrupted certificate is copied, `nginx -t` fails, the reload command is skipped, and Nginx continues serving traffic using the existing valid in-memory certificate without downtime.
- An alert is logged to host syslog for administrative investigation.

---

## 7. Storage Volumes & Database Backup

Persistent recruitment data is maintained in isolated named Docker volumes:

| Named Volume | Container Path | Purpose |
| :--- | :--- | :--- |
| `talentai_mongodb_data` | `/data/db` | Candidate records, batches, JDs, scores, and HR credentials |
| `talentai_mongodb_config`| `/data/configdb` | Internal MongoDB metadata |
| `talentai_uploads` | `/app/data/uploads` | Original uploaded resumes and batch ZIP archives |
| `talentai_extracted` | `/app/data/extracted` | Normalized extracted resume text |
| `talentai_failed` | `/app/data/failed` | Unparsable or rejected file quarantine |
| `talentai_logs` | `/app/logs` | Production audit and application logs |

### MongoDB Database Backup
To create a timestamped binary backup of the recruitment database:
```bash
docker compose exec mongodb mongodump \
  --username talentai_admin \
  --password <YOUR_PASSWORD> \
  --authenticationDatabase admin \
  --db talentai \
  --archive=/data/db/talentai_backup_$(date +%Y%m%d_%H%M%S).archive
```

### MongoDB Database Restore
To restore from an archive:
```bash
docker compose exec mongodb mongorestore \
  --username talentai_admin \
  --password <YOUR_PASSWORD> \
  --authenticationDatabase admin \
  --archive=/data/db/talentai_backup_YYYYMMDD_HHMMSS.archive \
  --nsInclude="talentai.*"
```

---

## 8. Graceful Shutdown & Maintenance

To safely stop the TalentAI production services:
```bash
docker compose down
```
During container shutdown, FastAPI's lifespan handler automatically:
1. Cancels in-flight ranking tasks cleanly.
2. Reconciles stale ranking jobs to `interrupted`.
3. Stops the retention maintenance worker and resume extraction worker.
4. Safely releases AI lifecycle resources.
5. Closes MongoDB connections without altering database records.
