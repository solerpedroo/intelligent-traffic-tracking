# Avaliação

Estado: protocolo e conversores implementados. O baseline real está bloqueado
porque [splits.json](../experiments/configs/splits.json) permanece
`test_split_frozen: false` e os hashes de sequência são nulos. Um relatório
dessa situação sai com `benchmark_eligible: false`. Não é resultado de teste
congelado.

## Comando

```bash
uv sync --locked --extra api --extra video --extra evaluation
.venv/bin/python scripts/evaluate.py \
  --ground-truth gt.json \
  --predictions artifacts/run \
  --protocol experiments/configs/evaluation-protocol.json \
  --splits experiments/configs/splits.json \
  --output experiments/reports/local.json \
  --frame-rate 25 --width 1280 --height 720 \
  --allow-development
```

Sem `--allow-development`, a CLI termina com código 2 e não grava métricas
enquanto o teste não estiver congelado. O relatório de desenvolvimento cobre
uma sequência por vez. Arquivos ausentes viram `not_evaluated` com motivo;
não são tratados como zero.

## O que cada métrica exige

- **Detecção:** `detections.csv` e boxes de referência. mAP@50:95 é a média,
  por classe com ground truth, do AP de 101 pontos do COCO nos limiares de IoU
  0,50 a 0,95. O pareamento é guloso por confiança, dentro do mesmo frame e da
  mesma classe. Classe sem ground truth fica fora da média.
- **MOT:** `tracks.csv` só com estado `observed`, e `track_id` na referência.
  Sem identidade anotada o status é `missing_identity_ground_truth`. HOTA, IDF1,
  MOTA e IDSW vêm do TrackEval 1.3.0, uma classe por execução, com essa classe
  gravada como pedestre MOTChallenge (id 1) e com pré-processamento de
  distratores desligado. Isso não é placar do MOTChallenge.
- **Contagem:** `crossing_events.csv` e janelas `[start_s, end_s]`. A tolerância
  congelada é 0,5 s para cada lado. O par é um para um, na mesma linha, classe
  e sentido. Erro relativo com contagem real zero é `null`; o erro absoluto
  continua presente.
- **Desempenho:** média, mediana e p95 por estágio em `timings.csv`. RAM e VRAM
  ficam `null` com motivo `not_instrumented`.

O frame interno 0 vira frame 1 do MOTChallenge. Um buraco no índice original
permanece buraco. Id 0 não é remapeado.

## Suíte

A suíte leve não instala TrackEval. O marcador `evaluation` cobre o caso
sintético perfeito e a troca de identidade conhecida. Fixtures sintéticas não
fecham o gate de dados descrito em [datasets.md](datasets.md).
