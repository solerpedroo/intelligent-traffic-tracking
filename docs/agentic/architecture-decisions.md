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

- Onda 0: versões suportadas, gerenciadores, lockfiles e schemas iniciais.
- Onda 1: decode/PTS/VFR, codecs, limites de entrada, dados e splits.
- Ondas 2–3: checkpoint, ByteTrack concreto, thresholds e classe da track.
- Ondas 4–5: tamanho mínimo, banda, lacuna máxima e regras temporais de dwell.
- Onda 7: formatos GT, tolerâncias de pareamento e agregações científicas.
- Onda 9: migrações, retenção/cotas, heartbeat, recuperação e contrato HTTP final.
- Onda 12: LICENSE e eventual plano de hospedagem, após verificar termos reais.
