# Mantra DevOps: Application Engineer Handoff & Access Packet

**Date:** October 2026  
**From:** Platform Engineer (Gargi)  
**To:** Application Engineer (Ayush Gourav / Bazzin07)  
**Project:** Mantra Industrial Knowledge Intelligence Platform  

---

## 1. Executive Summary & Action Summary

All 3 core prerequisites and the 2 pending items highlighted in your handoff review have been resolved and verified live:

| Item | Status | Details |
| :--- | :--- | :--- |
| **1. Repository Write Access / Patch** | **RESOLVED** | Unified patch `mantra-devops-platform.patch` generated; instructions provided for both patch application and GitHub collaborator invite. |
| **2. Reachable EC2 Server** | **RESOLVED** | EC2 instance `i-0d04109a558f3d149` has been **started**; permanent Elastic IP **`32.193.54.28`** is active and listening on ports `22`, `8000`, `3000`, and `9090`. |
| **3. Configured API Key & IAM/S3** | **RESOLVED** | Dedicated IAM Access Keys generated for `mantra-engineer1-app-owner`; master API key configured for production guard. |
| **4. Live AWS/S3 Verification** | **VERIFIED** | S3 bucket read/write tested live with scoped credentials (`verification_test.txt`); `/health` and `/ready` endpoints returning HTTP 200. |
| **5. Five NPM Vulnerabilities** | **RESOLVED** | All 5 frontend vulnerabilities (nanoid, postcss, source-map-js, vite, zod) patched; `npm run build` passing with 0 vulnerabilities. |

---

## 2. Repository Synchronization (Patch & Write Access)

### Option A: Apply the Unified Git Patch (Recommended)
A unified patch containing all 16 Platform DevOps commits (`upstream/main..HEAD`) has been created in the repository root:
`mantra-devops-platform.patch`

To apply it directly to your `Bazzin07/Mantra` repository:
```bash
git checkout main
git am mantra-devops-platform.patch
# Or alternatively:
git apply mantra-devops-platform.patch
```

### Option B: Direct Repository Collaborator Access
You can also push directly to the DevOps repository:
- **Repository:** `https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-.git`
- To accept the collaborator invite: check your GitHub notifications or email for `gaaarrrgiiiiiiiiiii/Mantra-devops-` collaborator invitation.

---

## 3. Server Deployment Access & Reachability

The EC2 instance was previously in a `stopped` state to manage cloud usage. It has been started and bound to the permanent Elastic IP:

- **Host Elastic IP:** `32.193.54.28`
- **SSH User:** `ubuntu`
- **SSH Key:** `~/.ssh/mantra-key.pem`
- **SSH Command:**
  ```bash
  ssh -i ~/.ssh/mantra-key.pem ubuntu@32.193.54.28
  ```
- **Application Directory on Server:** `/opt/mantra`
- **Docker Compose Command:**
  ```bash
  cd /opt/mantra
  sudo docker compose ps
  sudo docker compose logs -f backend
  ```

---

## 4. API Key & S3 / IAM Credentials

### A. Application API Key
The production guard in `backend/app/main.py` requires an API key in production mode. Use this key in headers (`x-api-key: <KEY>`) or queries:
```ini
IKI_REQUIRE_API_KEY=true
IKI_API_KEY=mantra_prod_sec_key_2026_x89
```

### B. Dedicated IAM S3 Credentials (Engineer 1)
These credentials belong to IAM user `mantra-engineer1-app-owner` and are attached to policy `mantra-engineer1-developer-policy`:
```ini
AWS_ACCESS_KEY_ID=<PROVIDED_PRIVATELY_TO_AYUSH>
AWS_SECRET_ACCESS_KEY=<PROVIDED_PRIVATELY_TO_AYUSH>
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=mantra-industrial-docs-657157860151
```

*Note: When running on the EC2 host, the backend automatically uses the attached EC2 IAM Instance Profile (`mantra-ec2-instance-profile`) without needing environment variables.*

---

## 5. Live Verification Endpoints

The following endpoints are live and operational on AWS:

1. **Liveness Health Check (HTTP 200):**
   ```
   http://32.193.54.28:8000/health
   ```
   *Live Response:*
   ```json
   {
     "status": "healthy",
     "service": "mantra-backend",
     "environment": "production",
     "repository_backend": "postgres",
     "documents": 0
   }
   ```

2. **Readiness Probe (DB + Redis) (HTTP 200):**
   ```
   http://32.193.54.28:8000/ready
   ```
   *Live Response:*
   ```json
   {
     "status": "ready",
     "database": "connected",
     "redis": "connected"
   }
   ```

3. **Prometheus Metrics Feed:**
   ```
   http://32.193.54.28:8000/metrics
   ```

4. **Grafana Operational Dashboard:**
   ```
   http://32.193.54.28:3000
   ```
   - User: `admin`
   - Password: `mantra_admin_2026`

5. **Prometheus Targets Status:**
   ```
   http://32.193.54.28:9090/targets
   ```

---

## 6. Shared-Access Security Limits & Boundaries

As documented in the Platform Architecture:
1. **Least-Privilege S3 Storage**: Your IAM credentials can List, Get, Put, and Delete objects within `arn:aws:s3:::mantra-industrial-docs-657157860151/*`. Administrative AWS actions (IAM changes, VPC alterations, EC2 termination) are restricted.
2. **Network Perimeter**:
   - Ports `22` (SSH), `8000` (FastAPI), `3000` (Grafana), `9090` (Prometheus) are reachable.
   - Internal databases (`PostgreSQL:5432` and `Redis:6379`) are isolated inside the Docker bridge network and not exposed to the public internet for security.
3. **Frontend Vulnerabilities**: All 5 npm vulnerabilities in `frontend/package.json` have been resolved. The production build (`tsc -b && vite build`) executes cleanly with 0 warnings.
