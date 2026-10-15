# Decisões arquiteturais

Este registro distingue diretrizes aceitas de escolhas ainda pendentes.
Aceitação documental não significa implementação. Novas entradas usam ID,
data, estado, contexto, decisão e consequências; ao substituir uma decisão,
referenciar a anterior sem apagar seu histórico.

## ADR-001 — Contexto compartilhado e entrega por ondas

- Data: 2026-10-15. Estado: aceito para planejamento.
- Contexto: desenvolvimento alternado em Cursor e Codex, baseado no protocolo
  do projeto `computer-vision-processing-lab`.
- Decisão: AGENTS, plano, cartões, workboard, ADRs e handoffs são o contexto
  durável. Papéis podem ser exercidos por um único agente sequencialmente.
- Consequência: nenhuma onda de código é concluída por existir sua documentação.

## ADR-002 — Núcleo → avaliação → web

- Data: 2026-10-15. Estado: aceito para planejamento.
- Contexto: há divergência de ordem entre as seções 11 e 20 do escopo.
- Decisão: seguir a orientação final da seção 20, avaliando o baseline e
  realizando os experimentos mínimos antes da aplicação web completa.
- Consequência: ondas 0–6 núcleo; 7–8 ciência; 9–11 produto; 12 aceitação.
  O scaffold web inicial não antecipa features de interface.

## ADR-003 — Isolamento científico e execução local

- Data: 2026-10-15. Estado: aceito para planejamento, conforme escopo §§4 e 17.
- Decisão: `vision/` independente de HTTP; CLI e worker compartilham pipeline.
  FastAPI e worker são processos distintos, SQLite e filesystem no MVP,
  um worker com um job ativo; CPU funcional, GPU opcional.
- Consequência: infraestrutura cloud, filas distribuídas e novo storage não são
  pré-requisitos; troca futura não pode exigir reescrever os contadores.

## ADR-004 — Geometria, tempo e identidade

- Data: 2026-10-15. Estado: aceito para planejamento.
- Decisão: BGR uint8 no decode; boxes xyxy em pixels originais; geometria
  normalizada; frames zero-based e tempo da mídia original. IDs locais à
  execução; `run_id` identifica a CLI e mapeia para `job_id` na API.
  Linha orientada tem A negativo/B positivo pelo produto vetorial; ROI inclui
  borda. Crossing considera segmento finito e deduplica por execução/linha/ID/sentido.
- Consequência: testes de coordenadas e direção precedem editor web. A fonte
  concreta de PTS/VFR e tratamento de lacunas serão registrados na Onda 1.

## ADR-005 — Evidência científica e experimentos mínimos

- Data: 2026-10-15. Estado: aceito para planejamento.
- Contexto: robustez aparece como P2, mas três experimentos são exigidos no MVP.
- Decisão: executar A/B/C mínimos conforme critérios do escopo; expansões,
  fine-tuning e BoT-SORT ficam após baseline. MOT exige GT de IDs, contagem
  exige referência própria; métricas ausentes recebem motivo, nunca valor fictício.
- Consequência: seleção de dados começa na Onda 1; metas quantitativas surgem
  após medições, sem promessa antecipada de HOTA, IDF1 ou FPS.

## Decisões pendentes

- Onda 0: resolvido por ADR-006; versões exatas nos lockfiles.
- Onda 1: decode/PTS/VFR, codecs, limites de entrada, dados e splits.
- Ondas 2–3: checkpoint, ByteTrack concreto, thresholds e classe da track.
- Ondas 4–5: tamanho mínimo, banda, lacuna máxima e regras temporais de dwell.
- Onda 7: formatos GT, tolerâncias de pareamento e agregações científicas.
- Onda 9: migrações, retenção/cotas, heartbeat, recuperação e contrato HTTP final.
- Onda 12: LICENSE e eventual plano de hospedagem, após verificar termos reais.

## ADR-006 — Toolchain e contratos da fundação

- Data: 2026-10-15. Estado: aceito para implementação da Onda 0.
- Decisão: baseline Python 3.12 (compatibilidade com o ecossistema científico),
  uv e uv.lock; Node 24 LTS, npm e package-lock.json. Pacote raiz instala
  `vision`; extra `api` instala o backend, sem acoplar o núcleo ao FastAPI.
- Frontend usa Biome para lint/formatação, TypeScript e Vitest.
- Contratos usam Pydantic v2 congelado, campos extras rejeitados e números
  finitos; NumPy somente para o contrato de frame. Frames são objetos internos
  não serializáveis em JSON; snapshots de configuração usam coleções imutáveis.
- Catálogo JSON empacotado começa vazio; nenhum ID/checkpoint fictício. Health
  indica liveness do serviço, não disponibilidade de modelos ou worker.
- Configuração do servidor via TRAFFIC_*; CORS explícito e restrito aos origins
  locais por padrão. Cliente futuro usa NEXT_PUBLIC_API_URL, validada em sua fronteira.
- Consequência: CI testa Python 3.12 e 3.14, instalação do núcleo sem extras API,
  API com health e shell Next.js. Modelos, vídeo, persistência e filas entram
  somente nas ondas responsáveis. Hashes/versões exatas ficam nos lockfiles.

### Evidência de compatibilidade da toolchain

O ambiente inicial possui Python 3.14 e Node 24; uv provisionou Python 3.12
sem alterar o Python do sistema. O cliente de testes exigido pelo Starlette
resolvido é httpx2; a dependência de desenvolvimento acompanha essa API.
Biome substitui o conjunto ESLint/Next que trouxe um advisory transitivo sem
correção disponível na versão consultada. Não se usa override incompatível
nem se ignora esse advisory. O contrato de checks (lint, tipos, testes e build)
permanece o mesmo. Referências: [Next.js](https://nextjs.org/docs/app/getting-started/installation),
[uv](https://docs.astral.sh/uv/concepts/projects/sync/),
[Biome](https://biomejs.dev/installation/quick-start/).
