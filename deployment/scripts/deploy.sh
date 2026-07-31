#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "Deploying NOVA CORE to Kubernetes..."
kubectl apply -f deployment/kubernetes/configmap.yml
kubectl apply -f deployment/kubernetes/secret.yml
kubectl apply -f deployment/kubernetes/pvc.yml
kubectl apply -f deployment/kubernetes/deployment.yml
kubectl apply -f deployment/kubernetes/service.yml
kubectl apply -f deployment/kubernetes/ingress.yml
kubectl apply -f deployment/kubernetes/hpa.yml
echo "Deploy complete."
