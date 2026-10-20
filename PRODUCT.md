# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: React + TypeScript/Vite for the operating console; FastAPI + SQLite for a runnable local first release.

## Users

Customer-service agents and service-operation managers working in a desktop browser. Agents need to resolve customer conversations quickly; managers need to monitor queues, knowledge coverage, ticket SLA, and customer satisfaction.

## Product Purpose

Provide one operating console for customer conversations, AI-assisted responses, human handoff, tickets, knowledge management, and basic operational reporting. The first release demonstrates a complete and auditable service loop from a customer message to resolution and satisfaction feedback.

## Positioning

The product combines traceable knowledge-grounded replies with explicit, configurable human-handoff rules and a workflow that preserves all customer context for the assigned agent.

## Operating Context

The system is used repeatedly during working hours on a desktop screen. The delivery specification supplied in the linked Lark document is the source for the phase-one scope, session and ticket states, API conventions, AI guardrails, and success measures.

## Capabilities and Constraints

- Phase one includes session queues, customer conversations, FAQ robot responses, human transfer, basic tickets, knowledge management, operational dashboard, audit events, and local persistence.
- The development release uses seeded SQLite data and replaceable local adapters rather than external SSO, models, queues, vector databases, or channel vendors.
- The AI response path must cite a published knowledge item or decline to invent an answer and offer human service.
- Transfer conditions include a user request, low confidence, negative emotion, a sensitive intent, and repeated unresolved turns.
- Assumption: the first runnable delivery is a desktop-oriented local application. Production cloud deployment, external channels, and real model providers are later integration work.

## Evidence on Hand

- R&D specification: `https://bytedance.larkoffice.com/docx/AM72dnenYoHBCExsdh6cjuUWnth`
- No approved brand assets, production customer data, or production integration credentials have been provided.

## Product Principles

- Keep live service work immediately actionable.
- Preserve context, ownership, and state changes in every handoff.
- Treat generated responses and imported knowledge as evidence requiring clear sources and human verification.
- Make operational risks visible before they become SLA breaches.
- Build every core workflow behind a stable local API contract.
