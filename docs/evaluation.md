# Avaliação

Estado: baseline medido em 2026-10-16 nas sequências estáticas do MOT15.
O único teste congelado é `MOT15-PETS09-S2L1`. Desenvolvimento e validação
saem com `benchmark_eligible: false`.

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

## Baseline MOT15

Fonte: [MOT15](https://motchallenge.net/data/MOT15/), arquivo
`MOT15.zip` com 1.310.994.213 bytes e SHA-256
`4197530e8bff30fc9fb55565280b8235ab3cc9d16a2eca3ba95e7d5dcae3a5b4`.
Licença da página: CC BY-NC-SA 3.0; sequências de terceiros podem ter condições
adicionais. O zip oficial do Stanford Drone Dataset não respondeu.

Entraram só sequências que a página descreve como câmera parada e cuja
correlação de fase entre o primeiro, o meio e o último frame ficou abaixo de
0,15 pixel: `TUD-Stadtmitte`, `KITTI-17` e `PETS09-S2L1`. Cada JPEG virou um
frame H.264, sem descarte, com o FPS do `seqinfo.ini`. O box permanece no pixel
original. Pedestre do MOT15 foi mapeado para a classe COCO `person` (id 0)
antes de olhar qualquer score. A coluna de confiança 0 virou `ignore`.
Limiares do YOLO11n e do ByteTrack não foram alterados depois da medição.

Contagem permanece `not_evaluated` (`missing_crossing_events`): essas
sequências não anotam cruzamento de linha.

Hardware do manifesto: Intel Core i5-13420H, 12 CPUs lógicas, CPU, Linux
7.2.9-201.fc44. Commit registrado `cc6fcc3a723d91714620c1e786cda55a2201db6f`,
com árvore Git suja no momento da execução.

| Sequência | Split | mAP@50:95 | P/R em IoU 0,5 | HOTA | IDF1 | MOTA | IDSW | FPS de inferência |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MOT15-TUD-Stadtmitte | development | 0,3582147781079647 | 0,7952755905511811 / 0,8737024221453287 | 0,5912918391307889 | 0,7689497716894977 | 0,7863321799307958 | 9 | 25,968920973654114 |
| MOT15-KITTI-17 | validation | 0,21555442301515973 | 0,4224561403508772 / 0,8814055636896047 | 0,5357560839975977 | 0,7249240121580547 | 0,6120058565153733 | 9 | 27,05054353427732 |
| MOT15-PETS09-S2L1 | test | 0,3424146710288721 | 0,8026214340786431 / 0,9302949061662198 | 0,5741068924352991 | 0,7569897226212842 | 0,7982573726541555 | 30 | 24,428973188821793 |

O número de benchmark é só a linha de teste. Os JSON estão em
`experiments/reports/`. No PETS09, o mAP por escala foi 0,3782068947698728 em
`medium` e 0,09542668552569529 em `large`; `small` ficou `not_evaluated`.

## Suíte

A suíte leve não instala TrackEval. O marcador `evaluation` cobre o caso
sintético perfeito e a troca de identidade conhecida. Fixtures sintéticas não
fecham o gate de dados descrito em [datasets.md](datasets.md).
