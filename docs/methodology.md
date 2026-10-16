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

## Próximo gate

A Onda 8 pode usar este baseline. Contagem continua sem referência nestas
sequências. Não ajustar limiar olhando o teste `MOT15-PETS09-S2L1`.
