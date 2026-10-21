# Mantra: Detailed DevOps Implementation Plan for Two Engineers

**Project:** Mantra Industrial Knowledge Intelligence Platform  
**Architecture Model:** 2-Engineer Collaborative DevOps (Platform Owner vs. Application Owner)  
**Last Updated:** October 2026

---

## 1. Executive Summary & Division of Responsibilities

The primary objective is to demonstrate a production-grade DevOps lifecycle: Infrastructure as Code (IaC), containerization, automated configuration management, continuous integration and delivery (CI/CD), and observability.

```
               ┌────────────────────────────────────────────────────────┐
               │                MANTRA DEVOPS PLATFORM                  │
               └────────────────────────────────────────────────────────┘
                       │                                        │
                       ▼                                        ▼
      ┌─────────────────────────────────┐      ┌─────────────────────────────────┐
      │   TEAMMATE (Engineer 1)         │      │         YOU (Engineer 2)        │
      │        APPLICATION OWNER        │      │          PLATFORM OWNER         │
      ├─────────────────────────────────┤      ├─────────────────────────────────┤
      │ • FastAPI backend & endpoints   │      │ • AWS VPC, Subnets, EC2, IAM    │
      │ • PostgreSQL + pgvector + Redis │      │ • Terraform (IaC & S3 Backend)  │
      │ • Dockerfiles & docker-compose  │      │ • Ansible provisioning playbooks│
      │ • Pytest test suite & /health   │      │ • Jenkins CI/CD pipeline & ECR  │
      │ • Prometheus /metrics endpoint  │      │ • Prometheus & Grafana setup    │
      └─────────────────────────────────┘      └─────────────────────────────────┘
```

---

## 2. Engineer 1 Playbook: Application & Runtime DevOps (Your Teammate)

> **Role:** Application Owner  
> **Core Mandate:** Build, containerize, and test the multi-service application stack so it boots predictably on any machine with `docker-compose up` and exposes standard health and metric hooks.

### 2.1 Git Branching & Directory Structure
1. Create and work within the dedicated feature branch:
   ```bash
   git checkout -b feature/backend-api
   ```
2. Maintain the following folder structure:
   ```text
   mantra/
   ├── backend/
   │   ├── app/
   │   │   ├── main.py              # FastAPI entry point & routers
   │   │   ├── config.py            # Pydantic BaseSettings (loads env vars)
   │   │   ├── db.py                # PostgreSQL + pgvector connection pool
   │   │   ├── redis_client.py      # Redis cache client
   │   │   └── api/
   │   │       ├── health.py        # /health and /ready endpoints
   │   │       └── documents.py     # Document upload & vector search
   │   ├── requirements.txt         # Pinned Python dependencies
   │   └── Dockerfile               # Production multi-stage Docker image
   ├── tests/
   │   ├── conftest.py              # Pytest fixtures and mock client
   │   ├── test_health.py           # Healthcheck and smoke tests
   │   └── test_api.py              # Core logic & vector retrieval tests
   ├── docker-compose.yml           # 4-tier local orchestration
   └── .env.example                 # Template for required environment variables
   ```

---

### 2.2 Core Application Responsibilities

#### A. Health Checks (`/health` & `/ready`)
In `backend/app/api/health.py`, implement endpoints used by Jenkins, Docker, and Ansible to verify deployment success:
```python
from fastapi import APIRouter, status, Response
from app.db import check_db_connection
from app.redis_client import check_redis_connection

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Liveness probe: returns 200 if the process is up."""
    return {"status": "healthy", "service": "mantra-backend"}

@router.get("/ready", status_code=status.HTTP_200_OK)
def readiness_check(response: Response):
    """Readiness probe: validates database and cache connectivity."""
    db_ok = check_db_connection()
    redis_ok = check_redis_connection()
    
    if not (db_ok and redis_ok):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unready", "database": db_ok, "redis": redis_ok}
        
    return {"status": "ready", "database": "connected", "redis": "connected"}
```

#### B. S3 Document Integration (IAM Instance Profile Friendly)
In `backend/app/config.py` and `documents.py`, interact with S3 **without hardcoding AWS access keys**:
```python
import boto3
import os

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "mantra-industrial-docs")

def get_s3_client():
    # boto3 automatically uses the EC2 IAM Instance Profile attached by Engineer 2
    return boto3.client("s3")
```

#### C. Expose Prometheus Metrics (`/metrics`)
Install `prometheus-fastapi-instrumentator`:
```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Mantra API")
Instrumentator().instrument(app).expose(app)
```

---

### 2.3 Dockerfile & Docker Compose Delivery

#### Production `backend/Dockerfile`
```dockerfile
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim AS runner
WORKDIR /app

RUN useradd -m -u 1001 appuser
COPY --from=builder /root/.local /home/appuser/.local
COPY app/ ./app/

ENV PATH=/home/appuser/.local/bin:$PATH
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `docker-compose.yml`
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://mantra_user:mantra_pass@db:5432/mantra_db
      - REDIS_URL=redis://redis:6379/0
      - S3_BUCKET_NAME=mantra-industrial-docs
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: mantra_user
      POSTGRES_PASSWORD: mantra_pass
      POSTGRES_DB: mantra_db
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mantra_user -d mantra_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

---

### 2.4 Pytest Suite
Create unit and integration tests inside `tests/test_health.py` and `tests/test_api.py`.
* Ensure `pytest tests/` runs locally with 100% passes before issuing a Pull Request to `main`.

---

## 3. Engineer 2 Playbook: Cloud & Infrastructure DevOps (You)

> **Role:** Platform Owner  
> **Core Mandate:** Provision secure AWS resources via Terraform, automate host provisioning and application deployment using Ansible, configure Jenkins CI/CD with ECR, and build the monitoring stack.

### 3.1 Git Branching & Directory Structure
1. Create and work within the dedicated feature branch:
   ```bash
   git checkout -b feature/infra-terraform
   ```
2. Maintain the following structure:
   ```text
   mantra/
   ├── terraform/
   │   ├── backend.tf               # S3 remote state + DynamoDB lock
   │   ├── providers.tf             # AWS Provider
   │   ├── main.tf                  # VPC, EC2, IAM, Security Groups, S3
   │   ├── variables.tf             # Configurable input parameters
   │   └── outputs.tf               # Public IP, bucket names, instance IDs
   ├── ansible/
   │   ├── inventory/
   │   │   └── hosts.ini            # EC2 target IP & SSH identity
   │   └── playbooks/
   │       └── deploy.yml           # Automated deployment playbook
   └── Jenkinsfile                  # End-to-end CI/CD pipeline definition
   ```

---

### 3.2 Phase-by-Phase Platform Tasks

#### A. Phase 2 — IAM Access & Security Policies
1. **Developer IAM Policy for Engineer 1**:
   * S3 Read/Write access limited to `arn:aws:s3:::mantra-industrial-docs/*`.
   * CloudWatch log viewing access.
   * Do **not** grant administrator credentials.
2. **EC2 IAM Role (`MantraEC2InstanceRole`)**:
   * Attach directly to the EC2 instance via an Instance Profile.
   * Policies:
     * `AmazonS3FullAccess` (or scoped policy for `mantra-industrial-docs`).
     * `CloudWatchAgentServerPolicy` (for metrics and logs).
3. **SSH Access Configuration**:
   * Generate individual SSH key pairs (`mantra-eng1.pem` and `mantra-eng2.pem`).
   * Add public keys to `/home/ubuntu/.ssh/authorized_keys`.

#### B. Phase 5 — Terraform Infrastructure as Code
1. **Remote State Backend (`terraform/backend.tf`)**:
   ```hcl
   terraform {
     backend "s3" {
       bucket         = "mantra-terraform-state-2026"
       key            = "prod/mantra.tfstate"
       region         = "us-east-1"
       dynamodb_table = "mantra-terraform-locks"
     }
   }
   ```
2. **Infrastructure Definition (`terraform/main.tf`)**:
   * **VPC & Subnet**: Dedicated VPC with public routing.
   * **Security Group (`mantra-app-sg`)**:
     * Inbound: Port 80 (HTTP), Port 443 (HTTPS), Port 8000 (FastAPI), Port 22 (SSH only from specific IPs).
     * Outbound: All traffic allowed.
     * Deny public access to Postgres (5432) and Redis (6379).
   * **EC2 Instance**: `t3.medium` running Ubuntu 22.04 LTS.
   * **S3 Bucket**: `mantra-industrial-docs` with server-side encryption.

#### C. Phase 6 — Ansible Deployment Automation
Create `ansible/playbooks/deploy.yml`:
```yaml
---
- name: Deploy Mantra Application Stack
  hosts: app_servers
  become: yes
  tasks:
    - name: Update apt cache and install prerequisites
      apt:
        name: [apt-transport-https, ca-certificates, curl, gnupg, git]
        state: present
        update_cache: yes

    - name: Install Docker and Docker Compose plugin
      apt:
        name: [docker.io, docker-compose-v2]
        state: present

    - name: Ensure app directory exists
      file:
        path: /opt/mantra
        state: directory
        owner: ubuntu
        group: ubuntu

    - name: Copy docker-compose.yml to host
      copy:
        src: ../../docker-compose.yml
        dest: /opt/mantra/docker-compose.yml

    - name: Run Docker Compose stack
      community.docker.docker_compose_v2:
        project_src: /opt/mantra
        state: present

    - name: Verify application health
      uri:
        url: http://localhost:8000/health
        status_code: 200
      register: health_result
      until: health_result.status == 200
      retries: 10
      delay: 5
```

#### D. Phase 7 — Jenkins CI/CD Pipeline
Write `Jenkinsfile` at the root of the repository:
```groovy
pipeline {
    agent any

    environment {
        AWS_REGION     = 'us-east-1'
        ECR_REGISTRY   = credentials('ecr-registry-id')
        IMAGE_NAME     = 'mantra-backend'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Run Pytest') {
            steps {
                sh 'pip install -r backend/requirements.txt pytest'
                sh 'pytest tests/'
            }
        }

        stage('Static Analysis / SonarQube') {
            steps {
                sh 'echo "Running code quality analysis..."'
            }
        }

        stage('Build & Push Docker Image') {
            steps {
                script {
                    sh "docker build -t ${ECR_REGISTRY}/${IMAGE_NAME}:${GIT_COMMIT} ./backend"
                    sh "docker push ${ECR_REGISTRY}/${IMAGE_NAME}:${GIT_COMMIT}"
                }
            }
        }

        stage('Deploy via Ansible') {
            steps {
                sh 'ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/deploy.yml'
            }
        }

        stage('Smoke Test') {
            steps {
                sh 'curl --fail http://${TARGET_EC2_IP}:8000/health'
            }
        }
    }
}
```

---

## 4. The Collaboration & Hand-off Contract

To eliminate roadblocks, both engineers must follow this clear hand-off interface:

| Step | Engineer 1 (Application Owner) Hand-off | Engineer 2 (Platform Owner) Action |
| :--- | :--- | :--- |
| **1. AWS Access** | Requests S3 bucket name and permissions. | Provisions IAM user, S3 bucket, and instance profile. |
| **2. Containerization** | Delivers working `Dockerfile` and `docker-compose.yml`. | Verifies image builds cleanly and runs locally. |
| **3. Infrastructure** | Specifies port and memory requirements (e.g., 2GB RAM). | Deploys EC2 `t3.medium` via Terraform with required Security Groups. |
| **4. Testing** | Delivers passing `pytest tests/` and `/health` route. | Plugs tests and health check into Jenkins & Ansible. |
| **5. Observability** | Instruments app with `/metrics` route. | Configures Prometheus scrape target and builds Grafana dashboard. |

---

## 5. Distinction: Implemented vs. Planned Presentation Strategy

For academic or project reviews, clearly differentiate between what is operational and what represents the planned production evolution:

* **Currently Implemented:**
  1. Multi-tier Docker Compose stack (FastAPI, pgvector, Redis).
  2. Scoped AWS IAM roles and EC2 security group topology.
  3. Terraform IaC with S3 backend state.
  4. Ansible configuration playbook.
  5. Pytest automation and `/health` smoke testing.
* **Planned Production Evolution:**
  1. AWS EKS / Kubernetes migration (Deployment, Services, Ingress, HPA).
  2. Dedicated RDS PostgreSQL with vector extensions.
  3. Production Prometheus, Grafana, and Alertmanager cluster.
  4. Auto-scaling policy (2–10 pods at > 70% CPU).
