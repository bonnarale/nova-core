"""Consulting vertical tools for NOVA CORE.

Provides tools for generating proposals, reports, contracts, invoices,
and market research for consulting/services businesses.
"""

from __future__ import annotations

import logging
from typing import Any

from app.tools.base import ToolParam, ToolSpec
from app.tools.result import ToolResult
from app.tools.verticals.base import VerticalModule, VerticalTool

logger = logging.getLogger(__name__)


class SearchMarketTool(VerticalTool):
    """Search real market/competition data using DuckDuckGo."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="search_market",
            description="Search real market data and competitors using DuckDuckGo. Returns relevant results for market research.",
            category="consulting:market_research",
            parameters=[
                ToolParam(name="query", type="string", required=True, description="Search query for market research"),
                ToolParam(name="max_results", type="integer", required=False, description="Max results to return (default 5)", default=5),
            ],
            permission_level="read",
            tags=["market", "research", "competition"],
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        query = params["query"]
        max_results = params.get("max_results", 5)

        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))

            formatted = []
            for r in results:
                formatted.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                })

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": formatted,
                    "count": len(formatted),
                },
                message=f"Found {len(formatted)} results for '{query}'",
            )
        except ImportError:
            return ToolResult(
                success=False,
                error="duckduckgo-search not installed. Run: pip install duckduckgo-search",
            )
        except Exception as e:
            logger.error("Market search failed: %s", e)
            return ToolResult(
                success=False,
                error=f"Search failed: {str(e)}",
            )


class GenerateProposalTool(VerticalTool):
    """Generate a consulting proposal document."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="generate_proposal",
            description="Generate a consulting proposal with problem statement, solution, scope, timeline, and pricing.",
            category="consulting:document_generation",
            parameters=[
                ToolParam(name="client_name", type="string", required=True, description="Client company name"),
                ToolParam(name="project_brief", type="string", required=True, description="Project description and objectives"),
                ToolParam(name="scope", type="string", required=False, description="Project scope details"),
                ToolParam(name="timeline_weeks", type="integer", required=False, description="Estimated timeline in weeks", default=4),
                ToolParam(name="budget_range", type="string", required=False, description="Budget range (e.g., '$5,000 - $10,000')"),
                ToolParam(name="market_research", type="string", required=False, description="Market research context from search_market"),
                ToolParam(name="project_id", type="string", required=False, description="Project ID to attach document"),
            ],
            permission_level="write",
            tags=["proposal", "document", "consulting"],
            policy="approval_required",
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        client = params["client_name"]
        brief = params["project_brief"]
        scope = params.get("scope", "A definir según alcance detallado")
        timeline = params.get("timeline_weeks", 4)
        budget = params.get("budget_range", "A definir")
        market = params.get("market_research", "")

        content = f"""# Propuesta Comercial — {client}

## 1. Resumen Ejecutivo

{brief}

## 2. Problema / Necesidad

El cliente requiere solucionar las siguientes problemáticas:
- {brief}

## 3. Solución Propuesta

Proponemos una consultoría especializada que incluye:
- Diagnóstico inicial y análisis de situación actual
- Diseño de estrategia y plan de acción
- Implementación y acompañamiento
- Medición de resultados

## 4. Alcance del Proyecto

{scope}

## 5. Cronograma Estimado

| Fase | Duración | Entregable |
|------|----------|------------|
| Diagnóstico | 1 semana | Informe de hallazgos |
| Diseño | 1 semana | Plan estratégico |
| Implementación | {max(1, timeline - 2)} semanas | Ejecución guiada |
| Cierre | 1 semana | Informe final |

**Duración total estimada: {timeline} semanas**

## 6. Inversión

**Rango presupuestario: {budget}**

*Nota: El presupuesto final se definirá tras el diagnóstico inicial.*

## 7. Próximos Pasos

1. Revisión de esta propuesta
2. Alineación de expectativas
3. Firma de contrato
4. Inicio del proyecto

---
*Documento generado por NOVA CORE — Consulting Tools*
*Estado: BORRADOR — Pendiente de revisión y aprobación*
"""

        document = {
            "client": client,
            "type": "proposal",
            "content": content,
            "timeline_weeks": timeline,
            "budget_range": budget,
        }

        return ToolResult(
            success=True,
            data=document,
            message=f"Propuesta generada para {client}. Estado: BORRADOR — pendiente de aprobación.",
        )


class GenerateReportTool(VerticalTool):
    """Generate a consulting report document."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="generate_report",
            description="Generate a consulting report with diagnosis, findings, recommendations, and action plan.",
            category="consulting:document_generation",
            parameters=[
                ToolParam(name="client_name", type="string", required=True, description="Client company name"),
                ToolParam(name="project_name", type="string", required=True, description="Project or engagement name"),
                ToolParam(name="findings", type="string", required=True, description="Key findings from the engagement"),
                ToolParam(name="recommendations", type="string", required=True, description="Recommendations based on findings"),
                ToolParam(name="project_id", type="string", required=False, description="Project ID to attach document"),
            ],
            permission_level="write",
            tags=["report", "document", "consulting"],
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        client = params["client_name"]
        project = params["project_name"]
        findings = params["findings"]
        recommendations = params["recommendations"]

        content = f"""# Informe de Consultoría — {client}

## Proyecto: {project}

## 1. Resumen Ejecutivo

Este informe presenta los hallazgos y recomendaciones derivados del proceso de consultoría realizado con {client} en el marco del proyecto {project}.

## 2. Diagnóstico

### Metodología
- Entrevistas con stakeholders clave
- Análisis de documentación existente
- Benchmarking de mejores prácticas
- Evaluación de procesos actuales

### Hallazgos Principales

{findings}

## 3. Recomendaciones

{recommendations}

## 4. Plan de Acción

| Prioridad | Acción | Responsable | Plazo |
|-----------|--------|-------------|-------|
| Alta | Implementar recomendaciones críticas | Equipo cliente | 30 días |
| Media | Desarrollar plan de seguimiento | Consultor | 60 días |
| Baja | Documentar lecciones aprendidas | Ambos | 90 días |

## 5. Conclusión

El proceso de consultoría ha permitido identificar oportunidades significativas de mejora. La implementación de las recomendaciones propuestas permitirá {client} alcanzar sus objetivos estratégicos.

---
*Documento generado por NOVA CORE — Consulting Tools*
*Estado: BORRADOR — Pendiente de revisión y aprobación*
"""

        document = {
            "client": client,
            "project": project,
            "type": "report",
            "content": content,
        }

        return ToolResult(
            success=True,
            data=document,
            message=f"Informe generado para {client} — {project}. Estado: BORRADOR.",
        )


class GenerateContractTool(VerticalTool):
    """Generate a consulting contract document. REQUIRES APPROVAL."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="generate_contract",
            description="Generate a consulting services contract. REQUIRES FINANCIAL APPROVAL before finalizing.",
            category="consulting:financial",
            parameters=[
                ToolParam(name="client_name", type="string", required=True, description="Client company name"),
                ToolParam(name="client_representative", type="string", required=True, description="Client authorized representative"),
                ToolParam(name="services", type="string", required=True, description="Description of services to be provided"),
                ToolParam(name="total_amount", type="string", required=True, description="Total contract amount"),
                ToolParam(name="payment_terms", type="string", required=False, description="Payment terms (e.g., '50% upfront, 50% on completion')", default="50% adelanto, 50% contra entrega"),
                ToolParam(name="duration_weeks", type="integer", required=False, description="Contract duration in weeks", default=4),
                ToolParam(name="project_id", type="string", required=False, description="Project ID to attach document"),
            ],
            permission_level="admin",
            tags=["contract", "financial", "legal"],
            policy="approval_required",
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        client = params["client_name"]
        representative = params["client_representative"]
        services = params["services"]
        amount = params["total_amount"]
        payment = params.get("payment_terms", "50% adelanto, 50% contra entrega")
        duration = params.get("duration_weeks", 4)

        content = f"""# Contrato de Servicios de Consultoría

## Entre las partes

**PRESTADOR:** NOVA CORE Consulting
**CLIENTE:** {client}
**REPRESENTANTE DEL CLIENTE:** {representative}

## Objeto del Contrato

El presente contrato tiene por objeto la prestación de servicios de consultoría por parte del PRESTADOR al CLIENTE, según se detalla a continuación:

## Descripción de Servicios

{services}

## Plazo de Ejecución

**Duración: {duration} semanas** a partir de la firma del contrato.

## Condiciones de Pago

**Monto total: {amount}**

Condiciones: {payment}

## Obligaciones del Prestador

1. Ejecutar los servicios conforme a las especificaciones acordadas
2. Mantener confidencialidad sobre toda información del cliente
3. Presentar avances periódicos del proyecto
4. Entregables conforme al cronograma establecido

## Obligaciones del Cliente

1. Proporcionar información y acceso necesario para la ejecución
2. Designar un punto de contacto autorizado
3. Cumplir con los términos de pago establecidos
4. Revisar y aprobar entregables en los plazos acordados

## Confidencialidad

Ambas partes se comprometen a mantener estricta confidencialidad sobre toda información intercambiada durante la vigencia de este contrato.

## Resolución de Conflictos

Cualquier disputa será resuelta mediante negociación directa. En caso de no llegar a acuerdo, se recurrirá a mediación antes de acciones legales.

---
*Documento generado por NOVA CORE — Consulting Tools*
*ESTADO: BORRADOR — REQUIERE APROBACIÓN FINANCIERA*
*El contrato no tendrá validez hasta ser aprobado y firmado por ambas partes.*
"""

        document = {
            "client": client,
            "representative": representative,
            "type": "contract",
            "content": content,
            "total_amount": amount,
            "payment_terms": payment,
            "approval_required": True,
            "approval_category": "financial",
        }

        return ToolResult(
            success=True,
            data=document,
            message=f"Contrato generado para {client}. ESTADO: BORRADOR — REQUIERE APROBACIÓN FINANCIERA antes de considerarse válido.",
        )


class GenerateInvoiceTool(VerticalTool):
    """Generate an invoice/proforma document. REQUIRES APPROVAL."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="generate_invoice",
            description="Generate an invoice or proforma for consulting services. REQUIRES FINANCIAL APPROVAL before finalizing.",
            category="consulting:financial",
            parameters=[
                ToolParam(name="client_name", type="string", required=True, description="Client company name"),
                ToolParam(name="invoice_number", type="string", required=True, description="Invoice number (e.g., INV-2026-001)"),
                ToolParam(name="services", type="string", required=True, description="Description of services rendered"),
                ToolParam(name="amount", type="string", required=True, description="Invoice amount"),
                ToolParam(name="tax_rate", type="string", required=False, description="Tax rate (e.g., '21%')", default="21%"),
                ToolParam(name="due_date", type="string", required=False, description="Payment due date"),
                ToolParam(name="project_id", type="string", required=False, description="Project ID to attach document"),
            ],
            permission_level="admin",
            tags=["invoice", "financial", "billing"],
            policy="approval_required",
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        client = params["client_name"]
        invoice_num = params["invoice_number"]
        services = params["services"]
        amount = params["amount"]
        tax = params.get("tax_rate", "21%")
        due = params.get("due_date", "30 días desde emisión")

        content = f"""# FACTURA / PROFORMA

**Número: {invoice_num}**
**Fecha de emisión: __________**

## Datos del Cliente

**Cliente:** {client}

## Descripción de Servicios

{services}

## Detalle de Montos

| Concepto | Monto |
|----------|-------|
| Servicios de consultoría | {amount} |
| IVA ({tax}) | __________ |
| **TOTAL** | **__________** |

## Condiciones de Pago

**Vencimiento:** {due}

**Método de pago:** A definir

## Observaciones

- Esta factura/proforma está sujeta a aprobación financiera
- El pago no se considerará hasta confirmación de received
- Consultas: facturacion@nova-core.com

---
*Documento generado por NOVA CORE — Consulting Tools*
*ESTADO: BORRADOR — REQUIERE APROBACIÓN FINANCIERA*
*Esta factura no tiene validez hasta ser aprobada.*
"""

        document = {
            "client": client,
            "invoice_number": invoice_num,
            "type": "invoice",
            "content": content,
            "amount": amount,
            "tax_rate": tax,
            "due_date": due,
            "approval_required": True,
            "approval_category": "financial",
        }

        return ToolResult(
            success=True,
            data=document,
            message=f"Factura {invoice_num} generada para {client}. ESTADO: BORRADOR — REQUIERE APROBACIÓN FINANCIERA.",
        )


class ConsultingTools(VerticalModule):
    """Consulting vertical module — tools for consulting/services businesses."""

    @property
    def name(self) -> str:
        return "consulting"

    @property
    def description(self) -> str:
        return "Tools for consulting and services businesses: proposals, reports, contracts, invoices, and market research"

    def get_tools(self) -> list:
        return [
            SearchMarketTool(),
            GenerateProposalTool(),
            GenerateReportTool(),
            GenerateContractTool(),
            GenerateInvoiceTool(),
        ]
