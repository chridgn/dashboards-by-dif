# Deployment Guide

This project runs on a single EC2 instance behind Caddy, which handles TLS automatically via Let's Encrypt.

## Infrastructure

- **EC2**: t3.small (2 vCPU, 2 GB RAM) minimum; t3.medium recommended
- **Storage**: 20 GB gp3 EBS volume
- **Domain**: `dashboards.chridgn.dev` → EC2 public IP
- **Stack**: Docker + Docker Compose (Postgres, Airflow, Grafana, Caddy)

---

## EC2 Security Group

Only three inbound rules needed:

| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 22 | TCP | Your IP only | SSH |
| 80 | TCP | 0.0.0.0/0 | HTTP (Caddy redirects to HTTPS) |
| 443 | TCP | 0.0.0.0/0 | HTTPS |

All internal services (Grafana :3000, Airflow :8080, Postgres :5432) are bound to `127.0.0.1` in docker-compose and are unreachable from the public internet.

---

## DNS (Namecheap)

1. Log in → **Domain List** → **Manage** next to `chridgn.dev`
2. Go to **Advanced DNS** tab
3. Add one A record:

| Type | Host | Value | TTL |
|------|------|-------|-----|
| A Record | `dashboards` | `<EC2 public IP>` | Automatic |

Use an **Elastic IP** if you don't want the IP to change on stop/start.

Propagation: 5–15 minutes typically, up to 1 hour.

---

## First-Time Server Setup

```bash
# SSH in
ssh -i ~/.ssh/your-key.pem admin@<EC2-IP>

# Install Docker (one-liner)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker admin
# Log out and back in for the group change to take effect
```

---

## Deploy

```bash
# Clone the repo
git clone https://github.com/chridgn/dashboards-by-dif.git
cd dashboards-by-dif/src

# Copy .env from local machine (run from your local machine)
scp -i ~/.ssh/your-key.pem src/.env admin@<EC2-IP>:/home/admin/dashboards-by-dif/src/.env

# Start everything
sudo docker compose up -d
```

First run builds the Airflow image (~2–3 minutes). Subsequent deploys are faster.

---

## Verify

```bash
sudo docker ps -a
```

Expected steady state:

| Container | Status |
|-----------|--------|
| src-postgres-1 | Up (healthy) |
| src-airflow-init-1 | Exited (0) |
| src-airflow-scheduler-1 | Up (healthy) |
| src-airflow-webserver-1 | Up (healthy) |
| src-grafana-1 | Up |
| src-caddy-1 | Up |

Once DNS resolves, Caddy auto-provisions the TLS cert on the first request. Hit `https://dashboards.chridgn.dev` — it redirects to the Grafana dashboard in kiosk mode.

---

## Historical Backfill

Run once after the first deploy to populate the database with historical data.

```bash
# BLS: 1996–present (all CPI, unemployment series)
sudo docker exec src-airflow-scheduler-1 python /opt/airflow/scripts/backfill_bls.py

# EIA: full available history (CA gas, electricity, natural gas)
sudo docker exec src-airflow-scheduler-1 python /opt/airflow/scripts/backfill_eia.py

# FRED: full available history (Fed funds rate, mortgage rate, etc.)
sudo docker exec src-airflow-scheduler-1 python /opt/airflow/scripts/backfill_fred.py
```

Expected record counts after backfill:

| Source | Records |
|--------|---------|
| BLS | ~2,548 |
| EIA | ~2,110 |
| FRED | ~6,031 |

---

## Updates

To deploy new code:

```bash
# On EC2
cd /home/admin/dashboards-by-dif
git pull

# If docker-compose.yml or Dockerfile changed:
cd src && sudo docker compose up -d --build

# If only DAG files or Grafana JSON changed:
# No restart needed — Airflow and Grafana pick up file changes automatically
```

If `.env` changed locally, SCP it again before restarting:

```bash
scp -i ~/.ssh/your-key.pem src/.env admin@<EC2-IP>:/home/admin/dashboards-by-dif/src/.env
sudo docker compose up -d
```

---

## Useful Commands

```bash
# View logs for a service
sudo docker compose logs -f grafana
sudo docker compose logs -f airflow-scheduler

# Restart a single service
sudo docker compose restart grafana

# Check DB record counts
sudo docker exec src-postgres-1 psql -U dif -d dashboard \
  -c "SELECT source, COUNT(*) FROM metrics.economic_indicators GROUP BY source;"

# Trigger a DAG run manually
sudo docker exec src-airflow-scheduler-1 airflow dags trigger data_collection
```
