#!/usr/bin/env bash
# ============================================================
# deploy.sh — Build, push to ECR, and deploy to ECS Fargate
#
# Prerequisites:
#   - AWS CLI v2 installed and configured
#   - Docker installed
#   - ECR repository exists
#   - ECS cluster + service exist (or use --create-infra)
#
# Usage:
#   ./scripts/deploy.sh [--env prod|staging] [--region us-east-1]
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ---- Config ----
ENV="${1:-prod}"
REGION="${2:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
ECR_REPO="${ECR_REPO:-nexus-api}"
ECS_CLUSTER="${ECS_CLUSTER:-nexus-${ENV}}"
ECS_SERVICE="${ECS_SERVICE:-nexus-api-${ENV}}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"

echo "=== Deploying Nexus API ==="
echo "  Environment : ${ENV}"
echo "  Region      : ${REGION}"
echo "  Account     : ${AWS_ACCOUNT_ID}"
echo "  Image       : ${IMAGE_URI}"
echo ""

# ---- 1. Build multi-stage image ----
echo "--- Building Docker image ---"
docker build \
  -f "${PROJECT_ROOT}/backend/Dockerfile.prod" \
  -t "${ECR_REPO}:${IMAGE_TAG}" \
  -t "${ECR_REPO}:latest" \
  "${PROJECT_ROOT}/backend"

# ---- 2. Authenticate with ECR ----
echo "--- Authenticating with ECR ---"
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# ---- 3. Tag and push ----
echo "--- Pushing image to ECR ---"
docker tag "${ECR_REPO}:${IMAGE_TAG}" "${IMAGE_URI}"
docker tag "${ECR_REPO}:latest" "${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}:latest"
docker push "${IMAGE_URI}"
docker push "${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}:latest"

# ---- 4. Update ECS service ----
echo "--- Updating ECS service ---"
aws ecs update-service \
  --cluster "${ECS_CLUSTER}" \
  --service "${ECS_SERVICE}" \
  --force-new-deployment \
  --region "${REGION}"

echo ""
echo "=== Deploy complete ==="
echo "  Image : ${IMAGE_URI}"
echo "  ECS   : ${ECS_CLUSTER} / ${ECS_SERVICE}"
