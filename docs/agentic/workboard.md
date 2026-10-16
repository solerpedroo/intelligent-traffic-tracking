# Workboard

Estado em 2026-10-16: Ondas 0–8 concluídas. Onda 9 proposta.
Fonte única de progresso por onda. Evidências ficam nos cartões.

## Próxima tarefa

Onda 9 — API, worker e SQLite. Os estudos A/B/C estão em
[methodology.md](../methodology.md). Não tratar o teste MOT15 como conjunto
de ajuste.

## Ondas

- **0 — Fundação executável e contratos:** `done`; responsável Codex; [cartão](tasks/wave-0-foundation.md).
- **1 — Vídeo, timestamps, CLI e dados:** `done`; responsável Codex; [cartão](tasks/wave-1-video-cli.md).
- **2 — Detector YOLO e baseline:** `done`; responsável Codex; [cartão](tasks/wave-2-detection.md).
- **3 — ByteTrack e trajetórias:** `done`; responsável Codex; [cartão](tasks/wave-3-tracking.md).
- **4 — Linhas, direção e contagem:** `done`; responsável Codex; [cartão](tasks/wave-4-counting.md).
- **5 — ROI, permanência e heatmaps:** `done`; responsável Codex; [cartão](tasks/wave-5-zones-heatmaps.md).
- **6 — Exports e integridade do núcleo:** `done`; responsável Cursor; [cartão](tasks/wave-6-exports.md).
- **7 — Avaliação e benchmark:** `done`; responsável Cursor; [cartão](tasks/wave-7-evaluation.md).
- **8 — Experimentos A/B/C:** `done`; responsável Cursor; [cartão](tasks/wave-8-experiments.md).
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
