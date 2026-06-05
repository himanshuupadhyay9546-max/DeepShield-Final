# DeepShield Enterprise — Deployment Guide

## Local Development (Docker Compose)

```bash
# 1. Clone repo
git clone https://github.com/your-org/deepshield
cd deepshield

# 2. Copy env
cp .env.example .env

# 3. Start all services
docker compose -f infra/docker-compose.yml up --build

# 4. Init database
docker exec deepshield-api-1 alembic upgrade head

# 5. Access
# API:      http://localhost:8000/api/docs
# Frontend: http://localhost:3000
# MLflow:   http://localhost:5000
# Grafana:  http://localhost:3001  (admin/deepshield)
# Flower:   http://localhost:5555  (admin/deepshield)
# MinIO:    http://localhost:9001  (minioadmin/minioadmin)
```

---

## AWS Production Deployment

### Prerequisites
```bash
aws configure
eksctl version  # >= 0.175
kubectl version
helm version    # >= 3.14
```

### 1. Create EKS Cluster
```bash
eksctl create cluster \
  --name deepshield-prod \
  --region us-east-1 \
  --nodegroup-name standard \
  --node-type m5.2xlarge \
  --nodes 5 \
  --nodes-min 3 \
  --nodes-max 50 \
  --managed

# GPU node group for ML workers
eksctl create nodegroup \
  --cluster deepshield-prod \
  --name gpu-workers \
  --node-type g4dn.xlarge \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 20 \
  --node-labels accelerator=nvidia-gpu
```

### 2. Install cluster add-ons
```bash
# NVIDIA device plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/main/nvidia-device-plugin.yml

# AWS Load Balancer Controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=deepshield-prod

# cert-manager (TLS)
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set installCRDs=true

# Metrics server (for HPA)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### 3. Create RDS PostgreSQL
```bash
aws rds create-db-instance \
  --db-instance-identifier deepshield-prod \
  --db-instance-class db.r6g.xlarge \
  --engine postgres \
  --engine-version 16.2 \
  --master-username deepshield \
  --master-user-password "$(openssl rand -base64 32)" \
  --allocated-storage 200 \
  --storage-type gp3 \
  --multi-az \
  --deletion-protection
```

### 4. Create ElastiCache Redis
```bash
aws elasticache create-replication-group \
  --replication-group-id deepshield-redis \
  --description "DeepShield cache and queue" \
  --node-group-configuration "ReplicaCount=2,Slots=0-16383" \
  --cache-node-type cache.r6g.large \
  --engine redis \
  --engine-version 7.0 \
  --automatic-failover-enabled
```

### 5. Create S3 Bucket
```bash
aws s3api create-bucket \
  --bucket deepshield-media-prod \
  --region us-east-1

aws s3api put-bucket-encryption \
  --bucket deepshield-media-prod \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"}}]}'

# CloudFront distribution
aws cloudfront create-distribution \
  --distribution-config file://infra/aws/cloudfront-config.json
```

### 6. Deploy to Kubernetes
```bash
# Create secrets
kubectl create secret generic deepshield-secrets \
  --from-literal=JWT_SECRET="$(openssl rand -base64 48)" \
  --from-literal=DATABASE_URL="postgresql+asyncpg://..." \
  --from-literal=REDIS_URL="rediss://..." \
  --from-literal=S3_BUCKET="deepshield-media-prod" \
  -n deepshield-prod

# Apply manifests
kubectl apply -f infra/kubernetes/ -n deepshield-prod

# Verify
kubectl get pods -n deepshield-prod
kubectl get hpa  -n deepshield-prod
```

---

## Azure Deployment

```bash
# AKS cluster
az aks create \
  --resource-group deepshield-rg \
  --name deepshield-prod \
  --node-count 5 \
  --node-vm-size Standard_D4s_v3 \
  --enable-cluster-autoscaler \
  --min-count 3 --max-count 50

# GPU node pool
az aks nodepool add \
  --resource-group deepshield-rg \
  --cluster-name deepshield-prod \
  --name gpunodes \
  --node-count 3 \
  --node-vm-size Standard_NC6s_v3 \
  --node-taints sku=gpu:NoSchedule
```

---

## GCP Deployment

```bash
# GKE cluster
gcloud container clusters create deepshield-prod \
  --region us-central1 \
  --num-nodes 5 \
  --machine-type n2-standard-8 \
  --enable-autoscaling \
  --min-nodes 3 --max-nodes 50

# GPU node pool
gcloud container node-pools create gpu-pool \
  --cluster deepshield-prod \
  --region us-central1 \
  --num-nodes 3 \
  --machine-type n1-standard-8 \
  --accelerator type=nvidia-tesla-t4,count=1
```

---

## Scaling Targets

| Metric | Target |
|--------|--------|
| API pods | 3–50 (CPU-based HPA) |
| Detection workers | 5–100 (queue-depth HPA) |
| Daily uploads | 100,000+ |
| Concurrent users | 10,000+ |
| Total users | 1,000,000+ |

---

## Monitoring

- **Grafana**: `https://monitoring.deepshield.ai` — dashboards for API, ML, infra
- **MLflow**: `https://mlflow.deepshield.ai` — model experiments and registry
- **Flower**: `https://tasks.deepshield.ai` — Celery queue monitoring
- **Prometheus**: internal scraping every 15s

---

## Backup Strategy

```bash
# PostgreSQL — daily automated backup via RDS
# Retention: 30 days (production), 7 days (staging)

# S3 — versioning enabled, cross-region replication to us-west-2
# Model weights — EFS snapshots daily

# Run manual backup:
kubectl exec -n deepshield-prod deploy/deepshield-api -- \
  pg_dump $DATABASE_URL | gzip > backup_$(date +%F).sql.gz
```
