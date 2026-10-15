# Tracking e trajetórias — Onda 3

O preset `bytetrack-default` integra o ByteTrack concreto Ultralytics headless
8.4.177 com LAP 0.5.13. A escolha e suas limitações estão no
[ADR-010](agentic/architecture-decisions.md#adr-010--bytetrack-concreto-estado-temporal-e-trajetórias).
O catálogo (`traffic-video models`) publica defaults derivados de `TrackerConfig`.
Parâmetros efetivos ficam em config.json e manifest.json; o manifest registra a
implementação e as versões instaladas. Nada é baixado pelo tracker.

## Execução

```bash
uv sync --locked --extra api --extra video --extra detector
.venv/bin/traffic-video process input.mp4 --model yolo11n-coco \
  --checkpoint checkpoints/yolo11n.pt --tracker bytetrack-default \
  --output-dir artifacts/tracking-run
```

Um JSON parcial pode ser passado por `--tracker-config params.json`, por exemplo:

```json
{"track_buffer": 45, "history_points": 96, "min_observations": 5}
```

O CLI combina esse objeto com os defaults do preset e valida todos os campos.
O núcleo aceita `ProcessingConfig(tracker_config_id="bytetrack-default", tracker=...)`;
CLI e futuro worker compartilham `process_video`.

## Associação e tempo

- Defaults: high=0.25, low=0.1, new=0.25, buffer=30, match=0.8,
  fuse_score=true. Detector confidence=0.1; desenho=0.25, independente.
- High inclui score >= high; segundo estágio usa low < score < high.
  Score exatamente low não participa. Detecções fracas não iniciam IDs.
- match_thresh é teto de custo de associação, não IoU mínimo. O upstream usa
  IoU com fusão opcional de score no primeiro estágio; segundo estágio tem teto
  de custo IoU 0.5, confirmação 0.7 e deduplicação IoU-distance 0.15, fixos nesta versão.
- Cada frame selecionado avança o tracker, mesmo sem detecções. Buffer mede a
  diferença entre índice atual e última observação; recuperar somente até o
  limite inclusivo. Acima dele há novo ID, sujeito à confirmação.
- Frame stride=1. Índices originais consecutivos e PTS crescentes são exigidos;
  um recorte começa com tracker vazio. VFR preserva timestamps mas usa passo
  unitário no Kalman; grandes intervalos reais não expiram mais rapidamente.
- Associação agnóstica à classe; classe do primeiro candidato fica fixa por ID.
  Jitter de classe não alterna os agregados. Classe inicial errada e associações
  ambíguas continuam possíveis. Nenhuma reidentificação ou ID persistente.
- Primeiro update pode emitir IDs imediatamente; novas entradas posteriores
  precisam de segunda observação de alta confiança. Não se reconstrói a fase
  candidata retroativamente. Histórico e início referem-se à primeira emissão confirmada.

## Artefatos e memória

`tracks.csv` registra estados `observed` e `lost` por frame. Observed contém a
caixa original da detecção associada; lost contém estimativa Kalman, pode estar
fora da imagem e tem confiança vazia. Não interpretar lost como presença observada.

`trajectories.csv` contém apenas observações confirmadas, incluindo baixa confiança,
com run_id, video_id, frame_index, timestamp_s, track_id, classe estável, confiança,
xyxy e centro inferior em pixels originais. É gravado incrementalmente; nenhum
filtro de visualização ou elegibilidade remove evidências desse arquivo.

`track-lifetimes.csv` fecha cada ID emitido com início, última observação,
observed_span_s, número de observações, closure_reason e analysis_eligible.
`removed` inclui expiração/deduplicação upstream; `selection_end_censored`
indica fim do vídeo/recorte, sem inferir saída geométrica. Span inclui lacunas e
não é tempo de ocupação nem permanência em ROI. Elegibilidade depende de
min_observations (padrão 3) e permite descartar tracks curtas na análise.

Somente tracks vivas/perdidas mantêm deque de até history_points (64) pontos.
max_live_tracks (4.000) limita estado atual e falha explicitamente ao exceder;
o SDK retém no máximo 1.000 removidas. Contadores agregados são escalares.
Trajetórias completas ficam no disco. Overlay mostra IDs/boxes observados e
rastros recentes; não conecta segmentos separados por frames ausentes.

Timings inclui tracking_ms, abrangendo associação, histórico e escrita das linhas
de tracking, separado de renderização e inferência. Elapsed inclui inicialização.
Falhas mantêm `.partial` e failure.json, nunca summary completed. Publicação
numérica independente de renderização continua sendo trabalho da Onda 6.

## Validação e limites

```bash
.venv/bin/pytest
.venv/bin/pytest -m 'tracker or detector'
.venv/bin/python scripts/smoke_detector.py --checkpoint checkpoints/yolo11n.pt \
  --image data/detector-smoke-bus.jpg --tracker bytetrack-default \
  --output-dir artifacts/tracking-smoke
```

A primeira suíte não exige Torch ou pesos. A segunda executa ByteTrack real em
sequências de detecções controladas e YOLO real com assets locais preparados
conforme [inventário](model-inventory.md). Testes de tracking bloqueiam rede.
O smoke repete uma imagem quatro vezes: comprova conexão entre detector, tracker,
CSV e vídeo; não mede qualidade em tráfego ou oclusão natural. Inspecionar logs
para investigar IDs suspeitos; métricas MOT e ID switches confirmados dependem
GT e entram na Onda 7. GPU e CI remota não foram validadas nesta sessão.
