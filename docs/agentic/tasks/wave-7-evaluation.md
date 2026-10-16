# Tarefa: `wave-7-evaluation`

- Estado: done
- Onda: 7 — Avaliação e benchmark
- Responsável / ferramenta: Cursor
- Requisitos do escopo: M09, §§6, 10.1, 12.4
- Dependência: [wave-6-exports](wave-6-exports.md), concluída com evidências.
- Arquivos permitidos: vision/evaluation/, vision/datasets/, vision/tests/, experiments/configs/, experiments/reports/, scripts/, docs/datasets.md, docs/evaluation.md, docs/methodology.md, arquivos de dependências/lockfiles. Também este cartão, workboard e ADRs relevantes. Ampliação: AGENTS, README, plano e índice dos cartões no encerramento.
- Plano: [implementation-plan.md — Onda 7](../../implementation-plan.md).

## Objetivo verificável

Medir o baseline com referências válidas e protocolo congelado.

## Contratos e decisões

O protocolo numérico de ADR-014 não mudou. O teste foi atribuído antes da
inferência: `MOT15-TUD-Stadtmitte` desenvolvimento, `MOT15-KITTI-17` validação,
`MOT15-PETS09-S2L1` teste. Pedestre MOT15 mapeado para COCO `person` (id 0).
Confiança 0 da anotação vira `ignore`. Limiares do detector e do tracker
permaneceram os do catálogo.

## Critérios de pronto

- [x] Conversores GT e TrackEval validados sem erro de indexação.
- [x] Detecção, MOT, contagem/eventos e desempenho avaliados separadamente.
- [x] Resultados reais por sequência, agregações e limitações reproduzíveis.
- [x] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Referências perfeitas e erros conhecidos continuam na suíte. O benchmark real
usou o zip oficial do MOT15, só nas sequências de câmera parada.

## Fora desta tarefa

Métricas calculadas de GT inexistente, metas inventadas e ajuste de parâmetros no teste.

## Evidências e revisão

Medição em 2026-10-16. Zip local
`/home/solerpedroo/Downloads/MOT15.zip`, 1.310.994.213 bytes, SHA-256
`4197530e8bff30fc9fb55565280b8235ab3cc9d16a2eca3ba95e7d5dcae3a5b4`, igual ao
`Content-Length` obtido antes do servidor oficial. Vídeos e JPEG ficaram em
`data/`, fora do Git.

Correlação de fase, primeiro contra meio e último frame, abaixo de 0,15 pixel
nas três sequências. Frames decodificados: 179, 145 e 795, iguais ao
`seqLength`. Hardware: Intel Core i5-13420H, 12 CPUs, CPU. Manifesto com
commit `cc6fcc3a723d91714620c1e786cda55a2201db6f` e `git_dirty: true`.

### Resultados

Relatórios: `experiments/reports/MOT15-TUD-Stadtmitte.json`,
`MOT15-KITTI-17.json` e `MOT15-PETS09-S2L1.json`. Só o último tem
`benchmark_eligible: true`.

Teste `MOT15-PETS09-S2L1`: mAP@50:95 0,3424146710288721; precisão/recall em IoU
0,5 iguais a 0,8026214340786431 e 0,9302949061662198; HOTA 0,5741068924352991;
IDF1 0,7569897226212842; MOTA 0,7982573726541555; 30 ID switches. Inferência
24,428973188821793 FPS. Contagem `not_evaluated`, motivo
`missing_crossing_events`.

Desenvolvimento e validação estão na tabela de [evaluation.md](../../evaluation.md).
`KITTI-17` teve o mAP mais baixo, 0,21555442301515973. Não houve ajuste depois
disso.

### Comandos da suíte

- `.venv/bin/ruff check vision/tests/test_evaluation.py` e
  `.venv/bin/ruff format --check vision/tests/test_evaluation.py`: aprovados.
- `.venv/bin/pytest -q vision/tests/test_evaluation.py`: **9 testes aprovados**,
  1 deselecionado.
- `.venv/bin/pytest -q -m evaluation vision/tests/test_evaluation.py`: **1 teste
  aprovado**, 9 deselecionados.

### Limitações

- Contagem não tem anotação de linha. Não foi criada uma linha artificial.
- O MOT15 também contém câmeras em movimento; elas ficaram de fora.
- A codificação H.264 é lossy. Os boxes não foram reamostrados.
- A árvore Git estava suja durante a inferência.
- O Stanford Drone Dataset e o UA-DETRAC oficial continuam indisponíveis nos
  endereços consultados.

Conclusão: baseline de detecção e MOT registrado no teste congelado. Próxima
ação: Onda 8, sem mexer nos limiares desse teste.
