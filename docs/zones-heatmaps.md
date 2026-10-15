# ROI, permanência e heatmaps — Onda 5

`ZoneAnalytics` acompanha ocupação observada e visitas por ID/ROI.
`HeatmapAccumulator` acumula centros inferiores por classe/janela. CLI e futuro
worker compartilham essas implementações; configurações efetivas e geometria
ficam em config.json e manifest.json. [ADR-012](agentic/architecture-decisions.md#adr-012--roi-observada-censura-de-visitas-e-heatmaps-limitados)
registra decisões e limites.

## Uso e configuração

```bash
.venv/bin/traffic-video process input.mp4 --model yolo11n-coco \
  --checkpoint checkpoints/yolo11n.pt --tracker bytetrack-default \
  --analytics-config examples/analytics/zones.json \
  --output-dir artifacts/analytics-run
```

`--analytics-config` aceita AnalyticsConfig JSON. Campos omitidos usam defaults
do contrato. ROI e heatmap podem ser ativados separadamente; ambos exigem tracker.
Linhas continuam disponíveis simultaneamente com `--counting-config`. Sem zones
ou heatmap.enabled, o pipeline mantém o comportamento anterior.

- `zones`: até 16 zonas, cada uma com zone_id único e vertices normalizados [0,1].
  Polígonos simples com 3–64 vértices, sem repetir o primeiro no fechamento. Sem
  buracos; zonas podem sobrepor. Concavidade e ambas as orientações são aceitas.
  Área normalizada <=1e-10 é rejeitada. Borda inclusiva, tolerância geométrica 1e-10
  nas operações normalizadas. O ponto deve também estar no plano da imagem.
- `max_gap_s=0.5`: máximo inclusivo entre observações consecutivas para dwell;
  tolerância float de 1 ns. Um único frame perdido sempre interrompe a visita.
- `heatmap.enabled=false`: ativação explícita; não depende de ter ROI.
- `heatmap.class_ids=[]`: usar classes selecionadas do detector, limitadas a 16;
  lista explícita deve ser subconjunto delas, sem duplicatas. IDs inválidos são
  rejeitados antes de carregar pesos. Class mapping acompanha o manifest.
- Grade padrão 128×72, mínimo 8×8, máximo 256×256; `window_s=60`, mínimo 1 s.
- `sigma_cells=1.0`: gaussiana espacial, em células; permitido [0,10]. Zero desativa.
- `weighting="observations"`: única política disponível, sem ponderação temporal.

## Ocupação, eventos e visitas

O centro inferior da caixa observada determina presença. Lost/predicted não
constituem observações atuais. Zonas sobrepostas têm ocupações independentes;
somá-las pode contar o mesmo ID mais de uma vez. IDs e classes vêm do tracker,
não são identidades ou classes reais verificadas.

Transição consecutiva observada fora→dentro emite zone_enter; dentro→fora emite
zone_exit. Primeira observação já dentro abre visita censurada à esquerda com
boundary_censored, sem afirmar entrada. Motivos distinguem início da seleção,
primeira observação posterior e recuperação após perda.

Loss encerra a visita no último ponto observado dentro, com censura à direita,
e emite observation_lost no frame em que foi constatada. Motivos: missing_observation,
track_removed, out_of_image ou timestamp_gap. Se o ID reaparece dentro, começa
outra visita censurada. O fim da seleção fecha visitas abertas como
boundary_censored/selection_end, sem inventar saída geométrica.

observed_dwell_s soma dt apenas entre frames consecutivos observados dentro da
ROI, respeitando max_gap_s. Não atribui tempo às transições outside→inside e
inside→outside, nem à duração do último frame ou às lacunas. É estimativa amostrada,
com hipótese de continuidade entre observações; não garante permanência física
real, já que movimentos intermediários e erros de detecção podem ser desconhecidos.
Um único ponto dentro gera dwell zero. VFR usa PTS reais, sem multiplicar por FPS.

`visit_id` identifica cada trecho dentro de uma execução, independente de track_id.
Visitas curtas permanecem auditáveis; não usar o total de visitas como total de
veículos únicos. Reset limpa IDs de visita, métricas e estado. Apenas IDs vivos/
perdidos mantêm estado em memória; os registros completos são exportados.

## Heatmaps

Cada track observada da classe selecionada contribui uma unidade por frame na
célula do centro inferior, mesmo abaixo do threshold de desenho. Lost/predicted,
pontos fora da imagem e classes não selecionadas não contribuem. Heatmap abrange
imagem inteira, sem máscara de ROI. Coordenada na borda width/height pertence à
última célula. Grade indexada `[row_y,column_x]`, origem no canto superior esquerdo.

Janelas [start,end) ancoradas no zero original da mídia, inclusive em recorte.
Cada janela que tem frames processados gera um mapa por classe, incluindo grades
zero. Intervalos sem frames não geram mapas; ausência de arquivo não comprova
ausência de objetos. Uma janela e até 16 classes ficam em RAM; as grades brutas
ocupam no máximo 8 MiB. `finish()` é idempotente e exige reset antes de novo update.

NPZ contém raw (uint64) e smoothed (float64). A gaussiana usa raio ceil(3*sigma),
zero padding e correção global de massa: soma smoothed igual à soma raw, com
precisão numérica. Raw nunca é alterada pela suavização. PNG Inferno normaliza
cada mapa pelo próprio pico; mapa vazio é preto. Para comparar quantitativamente,
usar as grades e o índice, não só as cores dos PNGs.

Unidade: observações por célula, sem peso por duração/FPS, sem calibração física.
Objetos lentos/observados mais vezes deixam mais contribuições; vídeos VFR ou com
FPS diferentes podem produzir distribuições distintas. Não interpretar como
passagens únicas, pessoas/m², densidade física ou congestionamento.

## Artefatos

- zone_events.csv: ZoneEvent com frame/PTS de constatação, run/video/ID/classe/ROI,
  event_type, visit_id e reason. Motivo distingue perda de saída.
- zone_visits.csv: ZoneVisit com primeiro/último ponto dentro, tempo observado,
  quantidade de observações, flags left_censored/right_censored, motivos e frame/
  PTS de fechamento. Fechamento pode ocorrer depois do último ponto dentro.
- zone_occupancy.csv: uma linha por frame/ROI/classe selecionada, incluindo zeros;
  observed_count é número de IDs observados nessa combinação.
- heatmap_index.csv: classe, janela, unidade, grade, observações, sigma e caminhos
  dos NPZ/PNG em heatmaps/. Os nomes são gerados internamente, sem paths do usuário.
- summary.json.zones: visitas e agregados por ROI/classe, observed_dwell_s,
  presenças amostradas e pico de ocupação observada. summary.heatmap traz unidades,
  parâmetros, quantidade de janelas e contribuições por classe.
- trajectories.csv da Onda 3 conserva os pontos completos que originam os mapas.
- analytics_ms em timings.csv inclui atualização e exports durante frames; fechamento
  de visitas/última janela é incluído somente no elapsed total. Overlay mostra ROI
  e ocupação observada atual, sem filtro de confidence da visualização.

Arquivos são mantidos como .partial até sucesso; heatmaps ficam em heatmaps.partial
antes da publicação. Falha de preview preserva NPZ já escrito e sinaliza erro.
A Onda 6 consolidará estados de artefatos e publicação numérica quando só render falhar.

## Reprodução e evidências

```bash
.venv/bin/pytest
.venv/bin/pytest -m 'tracker or detector'
.venv/bin/python scripts/smoke_analytics.py --source data/vehicles.mp4 \
  --checkpoint checkpoints/yolo11n.pt --output-dir artifacts/analytics-smoke
```

Fonte já preparada conforme [inventário de dados](datasets.md); alternativa explícita
`--download-example` obtém o mesmo arquivo com hash fixado. Script deriva os mesmos
150 frames/1280×720/25fps da Onda 4 e registra hashes de fonte, derivação e config.
Confronta somas de visitas/ocupação/summary, run_id, massa raw/smoothed, índice e
trajetórias. É reconciliação de integração, sem GT independente ou métricas MOT.

Primeiro piloto local: 15 visitas previstas, 30 eventos de zona e seis mapas
(três janelas, classes car/truck), com 488 observações de carros e 95 de caminhões.
Soma de dwell observado 10.16 segundos-ID/ROI, que pode ultrapassar a duração de
seis segundos por simultaneidade. Há fragmentações, visitas curtas e registros
classificados como bus na aproximação; não foram validados como veículos reais.
Não ajustar thresholds para ocultar esses resultados. Nenhuma acurácia geral
ou permanência física foi estabelecida. Fonte/mídia permanecem locais, sem
redistribuição; condições e limites da fonte são os mesmos da Onda 4.

O workflow manual analytics_smoke reproduz o smoke com download explícito;
CI remota e GPU não foram executadas nesta sessão. Testes leves verificam oráculos
exatos e limites de memória; teste de integração usa ByteTrack concreto/detector
controlado em duas execuções VFR, com linhas e analytics ativados simultaneamente.
