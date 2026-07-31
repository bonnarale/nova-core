
## Pendiente - Seguridad
- [ ] Upgrade Next.js 14.2.35 -> 16.x (breaking change, requiere testing).
      Corre `npm audit` en /frontend para ver detalle de las 2 vulnerabilidades.
      Hacerlo antes de exponer la app fuera de localhost.

## Pendiente - Desarrollo real (no son bugs, falta construir)
- [ ] PRIORITARIO - Tools: implementar tracking real de herramientas
      (catálogo de tools disponibles, historial de ejecuciones con
      resultado/duración). Necesario para poder auditar qué hace NOVA
      cuando actúe de forma autónoma. Backend actual solo expone
      datos de orquestación interna (governor/autonomy), no un
      registro de tools ejecutadas.
- [ ] Observability: implementar métricas reales de request rate,
      error rate, latencia p95/p99, y sistema de alertas. Backend
      actual solo expone counters/gauges vacíos y fase del lifecycle.
- [ ] Workflows: página de detalle es básica (solo muestra steps).
      Falta: iniciar ejecución, ver eventos en tiempo real, historial
      de ejecuciones (el backend ya tiene los endpoints:
      /executions, /executions/{id}/start, /executions/{id}/events).
- [ ] Workflows: constructor visual (drag & drop) es un placeholder
      sin funcionalidad real.

## Pendiente - Post-fusión de ramas (feature/real-agents-task-executor-pr3 + comprehensive-improvements-pr3)
- [ ] /api/v1/agents (standalone router) - import roto: app.agents.runtime no existe.
      Esta rama reestructuró agents/ con AgentManager en vez de AgentRuntime.
      No bloquea nada porque el frontend no lo usa directamente.
- [ ] /api/v1/tools (standalone router) - import roto: app.tools.context no existe.
      El frontend usa /nova-web/tools en su lugar, que sí funciona.
- [ ] Revisar los agentes reales con LLM (Planner, Researcher, Coder, Executor) de la
      rama real-agents-task-executor-pr3 y confirmar que siguen conectados/funcionando
      tras la fusión (no se probaron explícitamente hoy).
- [ ] Revisar MetaAgent / EvolutionEngine (auto-mejora) - tampoco se probó explícitamente.
- [ ] Considerar hacer commit de todo este estado actual en una rama limpia, ya que
      venimos trabajando directamente sobre el working directory sin commitear nada.
