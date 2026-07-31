# ADR-001: Kernel como Runtime Central

**Estado:** Aprobado

**Fecha:** 2026-07-07

## Contexto

NOVA CORE está diseñado como un sistema modular compuesto por una API, servicios de infraestructura, memoria, agentes y modelos de lenguaje.

En la arquitectura inicial, FastAPI actúa como punto de entrada principal y coordina la inicialización de los distintos servicios.

Sin embargo, el objetivo del proyecto es evolucionar hacia una plataforma donde múltiples fuentes puedan iniciar procesos, por ejemplo:

* solicitudes HTTP
* workflows de n8n
* tareas programadas
* eventos internos
* otros agentes
* futuras interfaces (CLI, WebSocket, MCP, etc.)

En ese escenario, la API no debe ser el centro del sistema.

## Decisión

El componente **Kernel** será el runtime central de NOVA CORE.

FastAPI será únicamente uno de los mecanismos de entrada al sistema.

Toda la lógica de coordinación deberá ejecutarse dentro del Kernel.

El Kernel será responsable de:

* iniciar el runtime
* registrar componentes
* administrar el ciclo de vida de las sesiones
* enrutar solicitudes
* publicar y consumir eventos
* administrar el contexto de ejecución
* coordinar la comunicación entre agentes

La API nunca deberá contener lógica de negocio.

## Arquitectura

```text
                HTTP
                  │
                  ▼
             FastAPI API
                  │
                  ▼
            Kernel Engine
                  │
     ┌────────────┼────────────┐
     ▼            ▼            ▼
  Router      Registry      Context
     │            │            │
     └────────────┼────────────┘
                  ▼
               Agents
                  │
                  ▼
     ModelGateway / Memory / Services
```

## Consecuencias

### Beneficios

* Separación clara entre infraestructura y lógica.
* Posibilidad de múltiples interfaces de entrada.
* Mayor facilidad para pruebas.
* Mejor escalabilidad.
* Integración sencilla de nuevos agentes.
* Menor acoplamiento entre módulos.

### Restricciones

* Ningún agente deberá depender directamente de FastAPI.
* FastAPI no deberá comunicarse directamente con los modelos.
* FastAPI no deberá contener reglas de negocio.
* El Kernel será el único responsable de la orquestación.

## Principio de diseño

> Toda ejecución significativa dentro de NOVA CORE debe atravesar el Kernel.

Este principio convierte al Kernel en el núcleo operativo del sistema y establece un punto único de coordinación para futuras extensiones.
