# NOVA CORE Frontend Platform

## Overview
React/Next.js web application for NOVA CORE providing comprehensive dashboards, chat, workflow management, and monitoring.

## Tech Stack
- **Framework**: Next.js 14 (App Router)
- **UI**: React 18, TypeScript 5
- **Styling**: Tailwind CSS 3
- **State**: Zustand 4
- **Testing**: Jest + React Testing Library

## Directory Structure
```
frontend/
  app/                    # 29+ route pages (App Router)
    layout.tsx            # Root layout with Sidebar + Header
    page.tsx              # Redirects to /dashboard
    dashboard/page.tsx    # System overview
    chat/page.tsx         # Real-time agent chat
    agents/page.tsx       # Agent management
    workflows/page.tsx    # Workflow builder
    goals/page.tsx        # Goal tracking
    tasks/page.tsx        # Task management (table + board view)
    knowledge/page.tsx    # Memory explorer
    rag/page.tsx          # RAG collection management
    models/page.tsx       # Model provider management
    tools/page.tsx        # Tool registry
    plugins/page.tsx      # Plugin management
    scheduler/page.tsx    # Cron job management
    events/page.tsx       # Real-time event feed
    observability/page.tsx # Metrics, traces, logs
    deployment/page.tsx   # Deploy history + rollback
    scaling/page.tsx      # Auto-scaling config
    security/page.tsx     # Security audit
    enterprise/page.tsx   # Enterprise features
    settings/page.tsx     # System settings
    admin/page.tsx        # Admin panel
    system/page.tsx       # Infrastructure health
    auth/page.tsx         # Login/register
    + autonomy, execution, learning, planning, profile, reasoning, vector-memory
  components/
    ui/                   # Button, Card, Badge, Input, Modal, Spinner, StatusBadge, Skeleton, EmptyState
    layout/               # Sidebar, Header
    dashboard/            # MetricCard, DataTable, StatBar, PageHeader, HealthGrid
    charts/               # BarChart, LineChart, PieChart
    chat/                 # MessageBubble, TypingIndicator
    workflow/             # WorkflowCanvas, WorkflowToolbar
    common/               # PageContainer, Section, LoadingScreen, ErrorFallback, ConfirmDialog, Toast
  hooks/                  # useApi, useWebSocket, useLocalStorage, useDebounce, usePolling, useEventSource
  stores/                 # Zustand stores: app, chat, cache
  themes/                 # Dark/light theme definitions
  types/                  # Shared TypeScript interfaces
  lib/                    # API client with interceptors, auth, retry
  services/               # Service layer wrapping API client
  public/                 # Static assets (health.html, index.html, styles.css)
```

## Getting Started
```bash
cd frontend
npm install
npm run dev
```

## Build
```bash
npm run build
```

## Test
```bash
npm test
```

## Architecture
- Consumes the existing NOVA CORE API Platform (FastAPI backend)
- Uses Python SDK and TypeScript SDK where available
- Does NOT duplicate any backend business logic
- Dark mode by default, full keyboard accessibility
- All API calls go through the centralized API client in `lib/api.ts`
