# Tarefa: `wave-11-analytics`

- Estado: done
- Onda: 11 — Analytics, comparação e metodologia
- Responsável / ferramenta: Cursor
- Requisitos do escopo: M08, §8.2
- Dependência: [wave-10-web-workspace](wave-10-web-workspace.md), concluída com evidências.
- Arquivos permitidos: frontend/, backend/app/api/, backend/app/services/, backend/app/schemas/, backend/tests/, docs/api-contract.md, docs/methodology.md. Também este cartão, workboard e ADRs relevantes.
- Plano: [implementation-plan.md — Onda 11](../../implementation-plan.md).

## Objetivo verificável

Apresentar números rastreáveis aos artefatos e comparações honestas.

## Contratos e decisões

ADR-017. A página lê `summary.json`, janelas, ocupação, lifetimes, heatmap e
manifest. Ausência fica `not_evaluated`. Zero só entra se o export o publicou.
Comparação com vídeo, trecho, geometria, pesos ou hardware diferentes não é
ablação.

Ampliação: a rota de preview ficou em `backend/app/routes.py` e
`backend/app/storage.py`, que é onde a lista de downloads já vivia. Também
AGENTS, plano, README e índice dos cartões no encerramento.

## Critérios de pronto

- [x] KPIs, séries, composição, ocupação, tracks, heatmaps e desempenho.
- [x] Comparison evidencia diferenças de dados, geometria, modelos e hardware.
- [x] Methodology/About, métricas ausentes e fragmentação com grau de evidência explícitos.
- [x] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Reconciliação com exports, vídeo curto, resultados vazios, GT ausente, métricas indisponíveis, jobs incompatíveis e E2E de consulta/comparação.

## Fora desta tarefa

Valores inferidos sem dados, congestionamento físico e alegações causais sem experimento controlado.

## Evidências e revisão

Em 2026-10-16:

- `.venv/bin/ruff check backend` aprovado.
- `.venv/bin/pytest -q`: **266 testes aprovados**, 17 deselecionados.
  Inclui o preview de heatmap e a rejeição de `../secret.png`.
- Em `frontend/`: `npm run lint`, `npm run typecheck`, `npm run test`
  (**25 testes**), `npm run test:e2e` (**2 testes Playwright**) e
  `npm run build` aprovados.
- O teste de analytics reconcilia a soma das janelas com `total_events` 2,
  preserva zero explícito num trecho curto, deixa FPS de inferência como
  `not_evaluated` quando o summary traz `null`, e não converte
  `observation_lost` em ID switch.
- O Playwright abre `/analytics?job=job-1`, lê "2 events" e o aviso de ground
  truth, e em `/experiments` recusa dois vídeos diferentes como ablação.

### Limitações

- Janelas vazias não são desenhadas: o CSV é esparso e a página diz isso.
- Não há galeria de ID switches confirmados porque os jobs do MVP não trazem
  ground truth de MOT. O painel permanece `not_evaluated`.
- Não houve novo smoke com heatmap real nesta onda. A rota foi testada com
  um PNG sintético no diretório do job.

Conclusão: os números visíveis apontam para o artefato, e a comparação declara
quando os jobs não podem ser lidos como experimento controlado. Próxima ação:
Onda 12.
