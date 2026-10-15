# Linhas, direção e contagem — Onda 4

O CLI e o futuro worker usam o mesmo LineCounter no pipeline. O contador recebe
somente tracks do adapter, usa o centro inferior da caixa e produz eventos
rastreáveis a observações. Não conta frames como veículos nem mantém identidade
física além do ID da execução. [ADR-011](agentic/architecture-decisions.md#adr-011--crossing-finito-confirmação-e-auditoria)
registra as decisões.

## Configuração e uso

```bash
.venv/bin/traffic-video process input.mp4 --model yolo11n-coco \
  --checkpoint checkpoints/yolo11n.pt --tracker bytetrack-default \
  --counting-config examples/counting/lines.json \
  --output-dir artifacts/counting-run
```

`--counting-config` lê CountingConfig JSON, com defaults dos campos omitidos.
Sem linhas, permanece o comportamento da Onda 3. Linhas exigem tracker. O núcleo
aceita `ProcessingConfig(counting=CountingConfig(...), ...)`. A configuração
resolvida, inclusive geometria, fica em config.json e manifest.json.

- `lines`: até 16 segmentos com line_id único, start/end normalizados em [0,1],
  distintos. Multiplicar x por width e y por height no plano contínuo original.
- `hysteresis_px=3`: distância perpendicular em pixels; pontos na borda da banda
  pertencem à banda. `0` é permitido, sem banda positiva.
- `stable_observations=2`: observações sucessivas fora da banda no mesmo lado
  para estabelecer cada lado. A banda interrompe a sequência de confirmação,
  preservando o último lado estabelecido.
- `min_observations=3`: mínimo de observações válidas dentro da imagem da track,
  necessário quando confirma crossing. Não emitir retrospectivamente um crossing
  rejeitado por track curta. Independente de tracker.min_observations, que marca
  elegibilidade de lifetimes para análise geral.
- `max_gap_frames=1`, `max_gap_s=0.5`: limites inclusivos entre observações
  usadas como evidência; ambos precisam ser atendidos. Tolerância float de 1 ns.
  Aumentá-los permite inferências através de lacunas e deve ser justificado.
- `window_s=60`: janelas fixas no tempo da mídia original, não no tempo de execução.

## Direção e geometria finita

Para start→end, A é o lado de produto vetorial negativo; B, positivo. Numa linha
horizontal da esquerda para a direita em coordenadas de imagem, A fica acima e
B abaixo. A_TO_B é negativo→positivo. Reverter endpoints reverte os sentidos.
A seta no vídeo indica start→end; não indica o movimento A_TO_B.

Exigir lados estáveis, interseção com o segmento finito e mínimo de observações.
O cálculo acompanha cada trecho observado, inclusive dentro da banda. Um desvio
por fora do endpoint não conta mesmo se a corda entre âncoras cortasse a linha.
Interseções nos endpoints são aceitas; deslocamento colinear é excluído. Toque
sem mudança estável de lado e jitter na banda não contam.

Lost/predicted não são observações. Ponto fora do plano [0,width]×[0,height] ou
lacuna excessiva invalida evidência geométrica. Preservar flags de eventos já
emitidos até a remoção do ID; nova observação precisa estabelecer lados de novo.
O contador exige frames consecutivos e PTS crescentes e é reiniciado por execução.
Somente IDs vivos/perdidos mantêm estado; sem histórico de todos os IDs em RAM.

Deduplicação por `(run_id,line_id,track_id,direction)`: o mesmo ID pode contar uma
vez em cada sentido de cada linha. Retornos posteriores na mesma direção não
rearmam. Nova identidade prevista pode duplicar o objeto físico; ByteTrack não
resolve esse problema universalmente.

## Artefatos

- `crossing_events.csv`: run/video/linha/ID/classe/sentido, frame e PTS originais
  da confirmação, tipo do evento e evidências: evidence_start_frame/s,
  intersection_xy e observed_count. Intersection é um par "x,y" em pixels dentro
  de um campo CSV com aspas. Observações completas ficam em trajectories.csv.
- `crossing_windows.csv`: agregação esparsa por linha/classe/sentido em intervalos
  `[window_start_s,window_end_s)`, calculados pelo PTS de confirmação. Janelas
  ancoradas em zero da mídia, mesmo em recorte. Campos ausentes significam zero;
  fim da última janela pode ultrapassar o trecho. Apenas a janela atual fica em RAM.
- `summary.json.counting`: total_events, by_line_class_direction e
  by_line_direction. Todos os sentidos das linhas têm total explícito, incluindo
  zero. Classes sem evento são omitidas da lista esparsa.
- `timings.csv`: counting_ms separado, incluindo atualização do contador e escrita
  dos eventos/janelas; flush final aparece somente no elapsed total.
- Vídeo: segmento orientado e totais A>B/B>A por linha, além de IDs e rastros.

Frame/timestamp do evento representam confirmação após a banda e estabilidade,
não o instante geométrico interpolado do crossing. Evidências permitem investigar
o atraso. Configs antigas sem counting continuam válidas; campos novos de evidência
são opcionais para ler o contrato mínimo antigo, mas sempre preenchidos pelo contador.
Falha de processamento preserva `.partial` e não publica summary completo.
Publicação numérica independente da renderização entra na Onda 6.

## Reprodução do piloto e limites

```bash
# Fonte local já obtida e hash verificado:
.venv/bin/python scripts/smoke_counting.py --source data/vehicles.mp4 \
  --checkpoint checkpoints/yolo11n.pt --output-dir artifacts/counting-smoke
# Alternativa explícita de obtenção do exemplo público:
.venv/bin/python scripts/smoke_counting.py --download-example \
  --checkpoint checkpoints/yolo11n.pt --output-dir artifacts/counting-smoke-downloaded
.venv/bin/pytest
.venv/bin/pytest -m 'tracker or detector'
```

O script usa somente a fonte com hash fixado, deriva os primeiros 150 frames em
1280×720/25fps e registra hashes da entrada derivada, fonte, anotação e configuração.
A transformação é anterior ao pipeline; as coordenadas originais dessa execução
são as da entrada derivada. `comparison.json` confronta cada evento uma única vez
por classe/linha/sentido e intervalo visual, com três frames de tolerância de
confirmação. Grava divergências antes de sinalizar erro. Não calcula métricas MOT.

Resultado local inicial: três eventos A_TO_B (dois carros e um caminhão), confirmados
nos frames 10, 14 e 24; três correspondências com a inspeção visual, sem eventos
faltantes ou extras nesse recorte. O carro branco tem frente parcialmente ocluída,
por isso sua anotação usa intervalo mais amplo. Não foram ajustados thresholds após
comparar o piloto. A anotação foi feita visualmente pelo agente, não por anotador
humano independente; não é split de teste congelado nem prova de qualidade geral.
Termos e limites da fonte em [datasets.md](datasets.md). Fonte/vídeo não são
versionados nem autorizados para redistribuição por essa checagem local.

O workflow manual `counting_smoke` oferece a mesma reprodução com download
explícito; execução remota não foi efetuada nesta sessão. Testes leves usam
trajetórias próprias com oráculos exatos; o teste de integração usa ByteTrack
concreto e detector controlado, não substitui o smoke completo YOLO real.
