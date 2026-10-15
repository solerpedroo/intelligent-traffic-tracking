# Tarefa: `wave-4-counting`

- Estado: done
- Onda: 4 — Linhas, direção e contagem
- Responsável / ferramenta: Codex
- Requisitos do escopo: M04, §§12.1, 14
- Dependência: [wave-3-tracking](wave-3-tracking.md), concluída com evidências.
- Arquivos permitidos: vision/geometry/, vision/counting/, vision/contracts/, vision/pipeline/, vision/tests/, examples/, docs/datasets.md, docs/architecture.md. Também este cartão, workboard e ADRs relevantes. Ampliação necessária: vision/rendering/, scripts/, CI, README, AGENTS, plano, índice dos cartões e docs/counting.md para overlay, smoke reproduzível e fechamento.
- Plano: [implementation-plan.md — Onda 4](../../implementation-plan.md).

## Objetivo verificável

Produzir contagens exatas em trajetórias sintéticas e eventos auditáveis no vídeo real.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [x] Segmentos finitos, lados A/B e histerese implementados.
- [x] Elegibilidade, lacunas e deduplicação por execução/linha/ID/sentido testadas.
- [x] Eventos por classe/sentido confrontados com pequena anotação manual.
- [x] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Horizontais/verticais/diagonais, ambos os sentidos, toque, jitter, passagem pela banda, extensão fora do segmento, desaparecimento, lacunas, fora da imagem, duas linhas/classes, retorno e reset.

Comandos e resultados executados estão registrados abaixo.

## Fora desta tarefa

Editor web, rearmamento de múltiplas travessias na mesma direção e solução universal para novos IDs.

## Evidências e revisão

Implementado em 2026-10-15. Revisão sequencial pelo Codex, sem subagentes.

- Contratos LineConfig/CountingConfig e CrossingEvent com evidência validada;
  configuração normalizada incorporada no manifest e config.json.
- Geometria finita e centro inferior; lados A/B por produto vetorial, histerese,
  estabilidade, elegibilidade e limites inclusivos em frames/segundos.
- LineCounter por execução, estado somente dos IDs vivos/perdidos. Flags por
  linha/sentido persistem através de lacunas, descartadas ao encerrar ID sem reuso.
- CSV incremental de eventos e janelas esparsas, summary reconciliável por
  linha/classe/sentido, timing próprio e overlay de linhas/totais legíveis.
- CLI `--counting-config`, exemplo normalizado e anotações visuais versionados.
  Script explícito de preparação/smoke real; CI manual counting_smoke preparada.

### Validação executada

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

- Python 3.12.15 e 3.14.8: **184 passed** na suíte leve, 14 deselected;
  **14 passed** nas integrações reais, 184 deselected, em cada versão.
- 45 casos novos: 44 leves e um integrado com ByteTrack concreto/detector
  controlado, que confirma crossing com detecções .15 não desenhadas. Integração
  bloqueia rede; não substitui o smoke de YOLO real.
- Oráculos exatos cobrem horizontais/verticais/diagonais, endpoints invertidos,
  dois sentidos, jitter, toque, banda, extensão, contorno de endpoint e movimento
  colinear, estabilidade, tracks curtas, desaparecimento, pontos fora da imagem,
  duas linhas/classes, retorno, deduplicação, reset, lacunas CFR/VFR e limites.
- Testes de memória com 1.000 IDs sequenciais retêm só um ID corrente; eventos e
  janelas saem em streaming. Testes reconciliam CSV/summary, zeros, limites decimais
  das janelas e comparação um-a-um com divergências faltantes/extras.
- Ruff/formatação/whitespace aprovados. Wheel/sdist construídos; wheel instalada
  isoladamente em /tmp/traffic-core-wave0 e um crossing real da máquina de estados
  executado com Python -I, sem Torch/lap/av/cv2/FastAPI instalados/importados.

```bash
.venv/bin/python scripts/smoke_counting.py --source data/vehicles.mp4 \
  --checkpoint checkpoints/yolo11n.pt --output-dir artifacts/wave-4-final-smoke
```

- Fonte pública vehicles.mp4, hash fixado no script/inventário, baixada localmente;
  derivação explícita dos primeiros 150 frames em 1280×720, 25fps, seis segundos.
  A câmera fixa e os objetos foram inspecionados visualmente pelo agente.
- Smoke final YOLO + ByteTrack + LineCounter CPU: **3 eventos A_TO_B**, sendo
  dois carros e um caminhão. Confirmações nos frames **10, 14 e 24** (0.40, 0.56,
  0.96 s). Três correspondências com intervalos de inspeção visual; **zero
  faltantes/extras nesse recorte**. Não usar como taxa geral de acerto.
- Evidências locais em `artifacts/wave-4-final-smoke/`: provenance.json com hashes
  de fonte/derivação/config/anotações, comparison.json, result/crossing_events.csv,
  crossing_windows.csv, summary, manifest e video.mp4. Eventos, janelas e summary
  reconciliados, run_id consistente. Todos os 150 frames do output reabertos e
  decodificados; overlay-preview.png inspecionado, linha/IDs/contadores legíveis.
- Anotação visual em examples/counting/manual-events.json e linha em lines.json:
  intervalos aproximados de crossing, tolerância de confirmação três frames;
  carro branco parcialmente ocluído tem intervalo maior. Rotulagem pelo agente,
  não por humano independente; desenvolvimento, sem split congelado ou GT MOT.
  Defaults de thresholds não ajustados após a comparação.

### Revisão e limites

Diff revisado quanto a sinal A/B, pixels originais, origem temporal, reset,
observações fracas, ausência/predição, estados limitados, publicação parcial e
reconciliação dos artefatos. Corrigidos durante a implementação: falsa interseção
pela corda entre âncoras em um contorno; contato com linha seguido de saída além
do endpoint; limites decimais de janelas e arredondamento de max_gap_s; evidências
parciais/futuras inválidas; extra api no job manual para coletar a suíte completa
antes de selecionar markers. YAML do workflow parseado e flags opt-in conferidas.
Nenhum bloqueador funcional restante no escopo da onda.

Novos IDs podem contar novamente o mesmo veículo, retornos repetidos na mesma
direção não rearmam, classe inicial do tracker pode estar errada e o evento é
atrasado pela confirmação. Máquinas de estado não substituem avaliação em GT.
Licença específica do vídeo de exemplo não estabelecida: mídia/derivados locais
ignorados no Git, sem redistribuição; fonte pública e limites em docs/datasets.md.
SDD, GT e splits científicos ainda pendentes; nenhum ID switch/HOTA/IDF1 calculado.
GPU, CI remota e frontend (não alterado) não executados. Falha apenas de render
com publicação numérica independente pertence à Onda 6. Editor web e ROI fora
desta tarefa.

Próxima ação: Onda 5 — ROI, permanência e heatmaps.

## Contratos antes de código

Adicionar LineConfig normalizada e CountingConfig (histerese, mínimo de observações, estabilidade e lacunas em frames/segundos), CrossingEvent auditável, LineCounter com reset e estado somente por ID vivo. CSV incremental e agregação por linha/classe/sentido/janela. A direção segue o produto vetorial do plano; confirmação no frame observado, sem estimar instante exato do crossing. ADR-011 registra os detalhes implementados.
