# Tarefa: `wave-5-zones-heatmaps`

- Estado: done
- Onda: 5 — ROI, permanência e heatmaps
- Responsável / ferramenta: Codex
- Requisitos do escopo: M05–M06
- Dependência: [wave-4-counting](wave-4-counting.md), concluída com evidências.
- Arquivos permitidos: vision/geometry/, vision/analytics/, vision/contracts/, vision/pipeline/, vision/rendering/, vision/tests/, docs/architecture.md. Também este cartão, workboard e ADRs relevantes. Ampliação: scripts/, examples/, CI, README, AGENTS, plano, índice dos cartões e docs/zones-heatmaps.md para reprodução, configurações e fechamento.
- Plano: [implementation-plan.md — Onda 5](../../implementation-plan.md).

## Objetivo verificável

Medir ocupação baseada em tracks e visualizar densidade de observações.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [x] ROI inclui borda e rejeita polígonos inválidos.
- [x] Presença, perda, entrada/saída e dwell com censura explícita.
- [x] Heatmaps por classe/janela com parâmetros e unidades registrados.
- [x] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Borda/vértice, zonas sobrepostas, entrada/saída, perda, início/fim dentro da zona, timestamps irregulares e acumulação conhecida de heatmap.

Comandos e resultados estão registrados abaixo.

## Fora desta tarefa

Densidade física por metro quadrado, velocidade real e inferência automática de congestionamento.

## Evidências e revisão

Implementado em 2026-10-15. Revisão exercida sequencialmente pelo Codex.

- ZoneConfig, AnalyticsConfig, HeatmapConfig e ZoneVisit; ZoneEvent ampliado com
  visit_id/reason, preservando leitura dos eventos mínimos anteriores.
- Polígonos simples normalizados, borda/vértice inclusivos, concavidade e winding
  reverso; validação de área, duplicações, cruzamentos, auto-toque e retrocesso.
- ZoneAnalytics com ocupação por PTS/ROI/classe e zeros explícitos; entradas/
  saídas observadas, loss, início/fim censurados e visitas em streaming. Dwell
  só entre observações consecutivas dentro, sem estender lacunas ou exposição final.
- Heatmaps observacionais por classe/janela, uma janela e até 16 grades em RAM;
  raw uint64 e smoothed float64 em NPZ, PNG Inferno e índice com unidades/params.
  Suavização não altera raw e conserva massa mesmo nas bordas da grade.
- CLI --analytics-config integrado ao mesmo pipeline de linhas/ByteTrack;
  manifest/config resolvidos, analytics_ms, overlay de ROI/ocupação.
- Exemplo e script de smoke reproduzível com fonte local/hash fixado; workflow
  manual analytics_smoke opt-in preparado. Nenhuma dependência nova.

### Comandos e resultados

```bash
.venv/bin/ruff check vision backend scripts
.venv/bin/ruff format --check vision backend scripts
.venv/bin/pytest
.venv/bin/pytest -m 'tracker or detector'
/tmp/traffic-py314/bin/pytest
/tmp/traffic-detector314/bin/python -m pytest -m 'tracker or detector'
/tmp/traffic-uv/uv build
git diff --check
```

- Python 3.12.15 e 3.14.8: **236 passed**, 15 deselected na suíte leve;
  **15 passed**, 236 deselected nas integrações reais, em cada versão.
- 53 casos novos: 52 leves e um integrado com ByteTrack real/detector controlado,
  rede bloqueada, duas execuções VFR, linhas e analytics simultâneos. Resets de
  visitas/mapas, censuras, mass conservation, CSV/summary/manifest e zeros conferidos.
- Oráculos de dwell com timestamps irregulares e um ponto isolado; gaps, loss,
  predicted, ID removido, fora da imagem, reentrada, primeiro/último frame dentro,
  sobreposição e duas classes. Geometria convexa/côncava, bordas/vértices, winding,
  auto-toque/crossing, colinearidade válida e inválida.
- Heatmap: contribuição exata por célula/classe/janela, pontos no limite da imagem,
  classes filtradas, intervalos sem frames, grades vazias, reset/finish idempotente,
  limite de classes/IDs e smoothing 0/.5/1/4 com massa em canto da grade.
- Memória: 500 IDs sequenciais deixam só um estado atual de ROI; 200 janelas
  mantêm só a grade corrente (512 bytes no teste 8×8×uint64), emitindo todas as
  janelas ao sink. Visitas reais completas não são armazenadas em listas no núcleo.
- Falha simulada de preview mantém NPZ numérico e sinaliza erro; classe inválida
  rejeitada antes de carregar checkpoint ou criar output. Lint/formatação/diff
  aprovados. Wheel/sdist construídos e wheel instalada em /tmp/traffic-core-wave0;
  Python -I executou ROI/dwell/heatmap bruto sem FastAPI/av/cv2/Torch/lap presentes.

```bash
.venv/bin/python scripts/smoke_analytics.py --source data/vehicles.mp4 \
  --checkpoint checkpoints/yolo11n.pt --output-dir artifacts/wave-5-final-smoke
.venv/bin/traffic-video process data/counting-pilot.mp4 --model yolo11n-coco \
  --checkpoint checkpoints/yolo11n.pt --tracker bytetrack-default \
  --analytics-config examples/analytics/zones.json --start-s 2.0 --end-s 2.6 \
  --output-dir artifacts/wave-5-cli-smoke
```

- Smoke final real YOLO/ByteTrack CPU: 150 frames, duas ROIs, 15 visitas previstas,
  30 eventos e seis mapas (classes car/truck × três janelas de 2s). Heatmaps: **488
  observações car e 95 truck**. Soma de dwell observado **10.16 segundos-ID/ROI**,
  agregada sobre objetos/zonas simultâneos, não permanência de um veículo único.
- Reconciliação scriptada: occupancy/visits/summary, quantidade de observações das
  visitas, run_id, índice, massa raw/smoothed e pontos da trajetória. Todos os
  150 frames do vídeo final reabertos e decodificados; overlay de zonas/ocupação
  e PNG de heatmap inspecionados visualmente.
- Artefatos locais em artifacts/wave-5-final-smoke/: provenance.json, smoke-report,
  result/zone_events.csv, zone_visits.csv, zone_occupancy.csv, heatmap_index.csv,
  heatmaps/*.npz e *.png, manifest/config/summary, vídeo e overlay-preview.png.
  Fonte/derivação/config com hashes; fonte já obtida na Onda 4, sem nova aquisição.
- CLI real: recorte [2.0,2.6), 15 frames, janela heatmap original [2,4) preservada,
  sem renumerar tempo. Contratos/parametrização via JSON funcionais.

### Revisão e limitações

Diff revisado para coordenadas originais, polígonos válidos, borda inclusiva,
perdas versus saídas, unidades, censura, reset/ordem, classe estável, escrita
incremental, uso de memória e compatibilidade de configurações antigas.
Ajustes de revisão: validar classes de mapa antes do load, rejeitar IDs duplicados,
finish idempotente, preservar massa de smoothing nas bordas e manter raw em falha
simulada de preview. Nenhum bloqueador funcional restante na Onda 5.

O piloto mostra fragmentação/visitas curtas e registros bus na aproximação,
sem validação de identidade/classe real; 15 visitas não significam 15 veículos.
Não foram ajustados thresholds para ocultar esses registros. Sem GT independente,
não atribuir acurácia, dwell físico, densidade por área ou ID switches confirmados.
Heatmaps são observações não ponderadas por dt; FPS e duração afetam os valores;
cores são normalizadas por mapa. Zonas sobrepostas não formam partição física.
Fonte e derivados continuam locais/ignorados no Git, com limites de uso descritos
em docs/datasets.md. CI remota, GPU e frontend (não alterado) não executados.
Publicação numérica independente de falha somente de render e contrato consolidado
de artefatos permanecem para a Onda 6; não foram declarados concluídos nesta onda.

Próxima ação: Onda 6 — exports, renderização e integridade do núcleo.

## Contratos declarados antes de código

ZoneConfig/AnalyticsConfig e HeatmapConfig; polígonos simples normalizados, borda inclusiva. ZoneEvent estendido com motivo/visita. Visitas, ocupação e eventos em streaming; dwell soma somente intervalos consecutivos observados dentro da ROI, sem preencher perdas, com censura inicial/final. Heatmap de observações por classe/janela, grades limitadas e saída numérica mais preview com suavização explícita. CLI/manifest integram parâmetros; ADR-012 registra as decisões implementadas.
