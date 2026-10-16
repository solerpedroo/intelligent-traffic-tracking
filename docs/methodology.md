# Metodologia do baseline

O protocolo numérico está congelado em
[evaluation-protocol.json](../experiments/configs/evaluation-protocol.json)
antes de existir um split de teste auditado. Mudar tolerância, limiares de IoU
ou o modo de AP é mudança de protocolo, não ajuste silencioso.

## Separação

Detecção, associação e contagem não compartilham denominador. Uma sequência só
com eventos de cruzamento não recebe HOTA. Uma sequência sem boxes não recebe
mAP. Ausência de referência é `not_evaluated` e o motivo fica no relatório.
Médias agregadas ignoram essas ausências; não as convertem em zero.

O teste congelado está em
[splits.json](../experiments/configs/splits.json): `MOT15-PETS09-S2L1`.
`MOT15-TUD-Stadtmitte` é desenvolvimento e `MOT15-KITTI-17` é validação.
A atribuição foi feita pela duração e pela descrição oficial, antes da
inferência. O Stanford Drone Dataset continua sem arquivo.

## O que não entra no baseline

- O piloto local de `vehicles.mp4` continua sendo checagem de desenvolvimento.
  Não substitui o teste congelado e não tem identidades MOT de referência.
- O baseline medido está em [evaluation.md](evaluation.md). Não há meta
  anterior de HOTA, IDF1 ou FPS; os números são os observados nesse hardware.
- Escala de objeto é um recorte por área do box (`small` < 32², `medium` < 96²,
  `large` no restante), não o tratamento de regiões `ignore` do COCO.
- TrackEval é executado por classe, com pré-processamento MOTChallenge
  desligado, para não tratar carro ou bicicleta como distrator de pedestre.

## Experimentos A/B/C

O protocolo foi gravado em
[wave8-protocol.json](../experiments/configs/wave8-protocol.json) antes das
novas execuções. Nenhum limiar foi escolhido depois de ver o teste.

- A altera um fator do ByteTrack por vez: `track_buffer` 10 e 60, `match_thresh`
  0,6 e 0,9. O detector permanece o YOLO11n do catálogo.
- B usa faixas fixas de densidade: sequência baixa abaixo de 5 objetos/frame,
  alta a partir de 8; frame baixo 0–4, médio 5–8, alto 9 ou mais. O MOT15 não
  tem flag de oclusão, então essa faixa fica `not_evaluated`.
- C aplica brilho 0,6, desfoque gaussiano com sigma 1,5 px, ruído gaussiano
  sigma 15 com seeds 0 e 1, e H.264 CRF 40. O ground truth não é deslocado.
  O ruído é a única condição aleatória e foi repetido nas duas seeds.

A interface da Onda 11 lê summary e CSV publicados. Contagem ausente,
ocupação ausente e MOT sem referência aparecem como `not_evaluated`, nunca
como zero. Dois jobs com vídeo, trecho, geometria, pesos ou hardware
diferentes não são tratados como ablação. Três sequências não sustentam
significância. O relatório completo está em
`experiments/reports/wave8-summary.json` e a figura do teste em
`experiments/reports/wave8-hota.svg`. Contagem continua sem anotação de linha.
