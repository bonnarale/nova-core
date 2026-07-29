#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "Activando entorno virtual..."
source .venv/bin/activate

echo "Levantando servicios Docker (Postgres, Redis, ChromaDB, Backend)..."
docker compose up -d 2>/dev/null || docker-compose up -d

echo "Esperando a que el backend esté listo..."
sleep 3

echo "Levantando frontend en segundo plano..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "======================================"
echo "NOVA CORE está iniciando."
echo "Frontend: http://localhost:3000"
echo "Backend health: http://localhost:8000/health"
echo "======================================"
echo ""
echo "Presiona Ctrl+C para detener el frontend."
echo "(Los contenedores Docker seguirán corriendo; usa 'docker compose down' para pararlos)"

wait $FRONTEND_PID
