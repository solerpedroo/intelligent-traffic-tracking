# Workboard

Estado em 2026-10-15: Ondas 0–6 concluídas. Onda 7 bloqueada no baseline real.
Fonte única de progresso por onda. Evidências ficam nos cartões.

## Próxima tarefa

Onda 7 — avaliação. Conversores, protocolo e TrackEval sintético estão no
cartão. O baseline real está bloqueado: o zip oficial em
`vatic2.stanford.edu` não respondeu em 2026-10-15; splits seguem sem hash.
Não iniciar a Onda 8 antes desse baseline.

## Ondas

- **0 — Fundação executável e contratos:** `done`; responsável Codex; [cartão](tasks/wave-0-foundation.md).
- **1 — Vídeo, timestamps, CLI e dados:** `done`; responsável Codex; [cartão](tasks/wave-1-video-cli.md).
- **2 — Detector YOLO e baseline:** `done`; responsável Codex; [cartão](tasks/wave-2-detection.md).
- **3 — ByteTrack e trajetórias:** `done`; responsável Codex; [cartão](tasks/wave-3-tracking.md).
- **4 — Linhas, direção e contagem:** `done`; responsável Codex; [cartão](tasks/wave-4-counting.md).
- **5 — ROI, permanência e heatmaps:** `done`; responsável Codex; [cartão](tasks/wave-5-zones-heatmaps.md).
- **6 — Exports e integridade do núcleo:** `done`; responsável Cursor; [cartão](tasks/wave-6-exports.md).
- **7 — Avaliação e benchmark:** `blocked`; responsável Cursor; [cartão](tasks/wave-7-evaluation.md).
- **8 — Experimentos A/B/C:** `proposed`; responsável não atribuído; [cartão](tasks/wave-8-experiments.md).
- **9 — API, worker e SQLite:** `proposed`; responsável não atribuído; [cartão](tasks/wave-9-jobs-api.md).
- **10 — Workspace, editor e viewer:** `proposed`; responsável não atribuído; [cartão](tasks/wave-10-web-workspace.md).
- **11 — Analytics, comparação e metodologia:** `proposed`; responsável não atribuído; [cartão](tasks/wave-11-analytics.md).
- **12 — Aceitação e portfólio:** `proposed`; responsável não atribuído; [cartão](tasks/wave-12-acceptance.md).

## Convenções

- `proposed`: planejado; `claimed`: em execução; `in_review`: aguardando revisão.
- `blocked`: impedimento registrado; `done`: critérios/evidências completos.
- Documentação inicial pronta não significa Onda 0 concluída.
- Mudanças de ordem/dependência precisam refletir plano, ADR e cartões.
- Ao dividir uma onda, vincular aqui seus cartões adicionais e preservar a visão de fechamento.
