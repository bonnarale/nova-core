#!/bin/bash
curl -s -X POST \
  -u admin:nova-core-n8n-admin-password \
  -H "Host:n8n.localhost" \
  -H "Content-Type: application/json" \
  -d '{"topic":"microservices","mode":"express","audit":false}' \
  http://127.0.0.1:80/webhook/deep-research
