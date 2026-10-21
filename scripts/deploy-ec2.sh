#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " [Step 1/5] Updating packages & installing prerequisites"
echo "=========================================================="
sudo apt-get update -y
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release git

echo "=========================================================="
echo " [Step 2/5] Installing Docker Engine & Docker Compose v2"
echo "=========================================================="
sudo apt-get install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker ubuntu

echo "=========================================================="
echo " [Step 3/5] Setting up /opt/mantra directory"
echo "=========================================================="
sudo mkdir -p /opt/mantra
sudo chown -R ubuntu:ubuntu /opt/mantra

echo "=========================================================="
echo " [Step 4/5] Syncing latest code from GitHub"
echo "=========================================================="
if [ ! -d /opt/mantra/.git ]; then
    git clone https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-.git /opt/mantra
else
    cd /opt/mantra
    git pull origin main
fi

cd /opt/mantra
if [ ! -f .env ]; then
    cp .env.example .env
fi

echo "=========================================================="
echo " [Step 5/5] Launching multi-container stack with Docker"
echo "=========================================================="
sudo docker compose down --remove-orphans || true
sudo docker compose up -d --build

echo "=========================================================="
echo " Verifying Container Health & API Status"
echo "=========================================================="
sudo docker compose ps

echo "Polling http://localhost:8000/health..."
for i in {1..15}; do
    if curl -s -f http://localhost:8000/health > /dev/null; then
        echo "SUCCESS: Mantra API is UP and HEALTHY!"
        curl -s http://localhost:8000/health
        echo ""
        exit 0
    fi
    echo "Waiting for backend service to initialize (attempt $i/15)..."
    sleep 4
done

echo "Check logs if not ready:"
sudo docker compose logs backend --tail 30
