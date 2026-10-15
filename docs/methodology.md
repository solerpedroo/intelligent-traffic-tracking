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

O conjunto de teste planejado está em
[splits.json](../experiments/configs/splits.json). Ele ainda não está congelado:
as três sequências candidatas do Stanford Drone Dataset não têm hash, auditoria
de câmera nem rótulos confirmados. Enquanto `test_split_frozen` for falso, a
CLI recusa o rótulo `frozen_test_benchmark`.

## O que não entra no baseline

- O piloto local de `vehicles.mp4` continua sendo checagem de desenvolvimento.
  Não substitui o teste congelado e não tem identidades MOT de referência.
- Não há meta de HOTA, IDF1 ou FPS. Esses números só serão definidos depois de
  um baseline medido no hardware e nas sequências reais.
- Escala de objeto é um recorte por área do box (`small` < 32², `medium` < 96²,
  `large` no restante), não o tratamento de regiões `ignore` do COCO.
- TrackEval é executado por classe, com pré-processamento MOTChallenge
  desligado, para não tratar carro ou bicicleta como distrator de pedestre.

## Próximo gate

Obter as sequências na fonte oficial, registrar URL, data, termos e SHA-256,
auditar câmera fixa e só então mudar `test_split_frozen` para verdadeiro no
mesmo commit que publica os hashes. A Onda 8 não começa antes desse baseline.
