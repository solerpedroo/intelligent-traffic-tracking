# Tarefa: `wave-6-exports`

- Estado: done
- Onda: 6 — Exports e integridade do núcleo
- Responsável / ferramenta: Cursor
- Requisitos do escopo: M07, M10, P0
- Dependência: [wave-5-zones-heatmaps](wave-5-zones-heatmaps.md), concluída com evidências.
- Arquivos permitidos: vision/pipeline/, vision/rendering/, vision/analytics/, vision/contracts/, vision/tests/, examples/sample_results/, docs/architecture.md, README.md. Também este cartão, workboard e ADRs relevantes. Ampliação: counting/trackers para colunas únicas, CLI, AGENTS, plano e índice dos cartões no encerramento.
- Plano: [implementation-plan.md — Onda 6](../../implementation-plan.md).

## Objetivo verificável

Consolidar artefatos reproduzíveis sem perder resultados numéricos por falha de vídeo.

## Contratos e decisões

Contratos afetados: schema de exportação 1.0, summary com avisos, manifest em
toda execução e sobrevivência numérica quando o MP4 não é publicado.
Decisão registrada em ADR-013 antes do fechamento. Não há novo formato de
evento; as colunas existentes passaram a ter uma fonte única.

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [x] CSV de eventos/tracks/zonas, summary, config e manifest versionados.
- [x] Vídeo com IDs, linhas, zonas, rastros e contadores.
- [x] Escrita final atômica, parciais explícitos e reprodução pela configuração.
- [x] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Pipeline curto completo, exports vazios, reconciliação eventos-summary, schemas, falha de codec, interrupção de escrita e reexecução da configuração.

## Fora desta tarefa

API de jobs, dashboard e resultados de benchmarks ainda não executados.

## Evidências e revisão

Verificação local em 2026-10-15, Python 3.12.15, no ambiente já sincronizado
com os extras `api`, `video` e `detector`. Não houve download de pesos nem de
vídeo real nesta onda.

### Comandos executados

- `.venv/bin/ruff check vision backend scripts`: aprovado.
- `.venv/bin/ruff format --check vision backend scripts`: 64 arquivos já formatados.
- `.venv/bin/pytest -q`: **242 testes aprovados**, 16 deselecionados (`detector`/`tracker`).
- `.venv/bin/pytest -q -m tracker`: **13 testes aprovados**, 245 deselecionados.
  Inclui o pipeline completo de zonas/heatmaps e a repetição sem MP4 anotado.

### O que a suíte cobre

- Schema 1.0, unidades e cabeçalhos de frames, detecções e timings.
- Export vazio de detecções com summary zerado e sem `failure.json`.
- Recarga de `config.json` por `model_validate_json` e repetição dos frames.
- `--no-annotated-video` e `render_annotated_video=false`: CSV/manifest/summary
  válidos, sem `video.mp4`, aviso `annotated_video_skipped`.
- Falha injetada de encoder: summary `completed_with_warnings`, 12 frames no CSV,
  MP4 não publicado.
- Escrita interrompida de `frames.csv`: `failure.json`, sem summary e sem CSV final.
- Pipeline ByteTrack com linhas, ROI e heatmap sem vídeo: visitas, eventos e
  observações do índice batem com o summary.

### Revisão

A renderização e o encode ficaram fora do caminho que publica os números.
Preview de heatmap com `imencode` falso conserva o NPZ e omite o PNG.
Falha de decode, tracker ou tabela continua sem summary de sucesso, como nas
ondas anteriores. Overlay de IDs, linhas, zonas e contadores permanece no fluxo
em que o MP4 é pedido; esta onda não reabre o desenho em si.

### Limitações

- CI remota não foi disparada nesta sessão.
- O encoder pode remover um MP4 vazio após falha; o estado explícito fica no
  summary, não num `.partial` garantido.
- Não há benchmark, GT novo nem métrica MOT. Ausência de referência continua
  `not_evaluated_no_ground_truth`.
- A Onda 7 segue bloqueada para fechamento enquanto os splits reais de
  [datasets.md](../../datasets.md) não forem auditados e congelados.

Conclusão: critérios da Onda 6 verificados localmente. Próxima ação: assumir o
cartão da Onda 7 sem inventar baseline.
