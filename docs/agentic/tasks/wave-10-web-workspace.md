# Tarefa: `wave-10-web-workspace`

- Estado: done
- Onda: 10 — Workspace, editor e viewer
- Responsável / ferramenta: Cursor
- Requisitos do escopo: §8, M01/M04/M05/M07 web
- Dependência: [wave-9-jobs-api](wave-9-jobs-api.md), concluída com evidências.
- Arquivos permitidos: frontend/, backend/app/api/, backend/app/schemas/, backend/tests/, examples/, .github/workflows/, docs/api-contract.md, README.md. Também este cartão, workboard e ADRs relevantes.
- Plano: [implementation-plan.md — Onda 10](../../implementation-plan.md).

## Objetivo verificável

Concluir upload, geometria, execução e inspeção pelo navegador.

## Contratos e decisões

ADR-016. O clique desconta o letterbox antes de normalizar. Os campos
numéricos editam o mesmo par. `GET /api/processing-defaults` entrega os
defaults do contrato. O worker passa o checkpoint verificado em
`TRAFFIC_CHECKPOINT_DIR`. Analytics e comparação ficam na Onda 11.

Ampliação necessária: as rotas reais estão em `backend/app/routes.py` e
`backend/app/main.py`, não em `backend/app/api/`. Também `backend/app/worker.py`,
`backend/app/db.py`, `backend/app/repository.py`, `backend/app/core/config.py`,
`vision/pipeline/video.py`, `.gitignore`, AGENTS, plano e índice dos cartões.

## Critérios de pronto

- [x] Overview, Workspace, Jobs e Viewer com catálogo/cliente tipado.
- [x] Editor normalizado com direção, linhas/zonas, resize/letterboxing e alternativa por campos.
- [x] Polling terminal, cancelamento, erros recuperáveis, vídeo e downloads acessíveis.
- [x] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Vitest para transformações do editor e estados; Playwright upload→linha→job→resultado→download; smoke local com núcleo real separado das fixtures leves da CI.

## Fora desta tarefa

Duplicação de contadores no frontend e analytics avançado da próxima onda.

## Evidências e revisão

Em 2026-10-16:

- `.venv/bin/ruff check` em backend e `vision/pipeline/video.py`: aprovado.
- `.venv/bin/pytest -q`: **265 testes aprovados**, 17 deselecionados.
- Em `frontend/`: `npm run lint`, `npm run typecheck`, `npm run test`
  (**21 testes**), `npm run test:e2e` (**1 teste Playwright**) e `npm run build`
  aprovados. O Playwright intercepta a API e percorre overview → upload →
  linha → job → viewer → download.

Smoke local, separado da fixture: API em `127.0.0.1:8000` com
`TRAFFIC_DATA_DIR=/tmp/traffic-wave10` e Next em `127.0.0.1:3000`. O vídeo
sintético de 4 frames, 160×96, foi enviado por HTTP. O workspace abriu esse
vídeo, a linha `line-1` (0.2,0.5)–(0.8,0.5) foi criada pelos campos, e o job
`dce5240d38f24b89b869270809bbc9b3` voltou 202 `queued`. O worker, com
`checkpoints/yolo11n.pt`, publicou `summary.json` com `selected_frames` 4 e
`video.mp4`. No viewer o elemento de vídeo carregou largura 160, sem erro de
mídia, e os links de download estavam visíveis.

A primeira listagem de jobs, antes do lock da migração, respondeu 500
(`table videos already exists`) por duas conexões simultâneas. Depois da
transação imediata, `test_parallel_connections_migrate_once` passou com 4
threads.

### Limitações

- O seletor de arquivo do navegador de verificação não foi exercido; o upload
  real entrou por HTTP e o controle de arquivo foi coberto pelo Playwright
  com API simulada.
- O job já concluído desse smoke ficou com `processed_frames` 0 porque o
  worker daquele processo ainda não gravava o total. O código seguinte grava
  `selected_frames` ao terminar. Não houve nova execução depois dessa correção.
- Gráficos, heatmaps e comparação entre jobs não fazem parte desta onda.

Conclusão: o fluxo de configuração e inspeção funciona no navegador, e o
worker publica o vídeo e o summary do job escolhido. Próxima ação: Onda 11.
