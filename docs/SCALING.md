# Scaling

## Overview

NOVA CORE provides load balancing, worker pools, queue management, caching, distributed locking, sharding, partitioning, replication, and autoscaling.

## Components

| Component | Package | Description |
|-----------|---------|-------------|
| Load Balancer | `app.scaling.load_balancer` | Round robin, least connections, weighted, health-aware |
| Worker Pool | `app.scaling.worker_pool` | Configurable size, priority queues |
| Queue Manager | `app.scaling.queue_manager` | Priority, delayed, retry, dead-letter queues |
| Cache | `app.scaling.cache` | LRU, TTL, FIFO strategies |
| Distributed Lock | `app.scaling.distributed_lock` | Timeout and lease renewal |
| Sharding | `app.scaling.sharding` | Hash-based and domain sharding |
| Partitioning | `app.scaling.partitioning` | Time and hash partitioning |
| Replication | `app.scaling.replication` | Read replicas with failover |
| Autoscaler | `app.scaling.autoscaler` | CPU, memory, queue depth metrics |
| Resource Manager | `app.scaling.resource_manager` | Resource monitoring |

## Load Balancing Strategies

| Strategy | Description |
|----------|-------------|
| Round Robin | Sequential distribution |
| Least Connections | Routes to least busy backend |
| Weighted | Distribution by configured weights |
| Health Aware | Skips unhealthy backends |

## Autoscaling

Automatically scales based on:

| Metric | Threshold |
|--------|-----------|
| CPU usage | > 80% scale up |
| Memory usage | > 85% scale up |
| Queue depth | > 100 scale up |
| Request rate | Monitored for trends |
| Execution latency | > 2s triggers scale |

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /scaling/health` | Scaling health |
| `GET /scaling/metrics` | Scaling metrics |
| `GET /scaling/statistics` | Statistics |
| `GET /scaling/workers` | Worker pool status |
| `GET /scaling/queues` | Queue status |
| `GET /scaling/cache` | Cache stats |
| `GET /scaling/resources` | Resource utilization |
| `POST /scaling/scale-up` | Scale up |
| `POST /scaling/scale-down` | Scale down |
| `POST /scaling/cache/clear` | Clear cache |
