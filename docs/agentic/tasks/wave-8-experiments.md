# Tarefa: `wave-8-experiments`

- Estado: done
- Onda: 8 — Experimentos A/B/C
- Responsável / ferramenta: Cursor
- Requisitos do escopo: M10, §§10, 14, 16
- Dependência: [wave-7-evaluation](wave-7-evaluation.md), concluída com evidências.
- Arquivos permitidos: experiments/, vision/evaluation/, vision/datasets/, vision/tests/, scripts/, docs/evaluation.md, docs/methodology.md. Também este cartão, workboard e ADRs relevantes. Ampliação: AGENTS, README, plano e índice dos cartões no encerramento.
- Plano: [implementation-plan.md — Onda 8](../../implementation-plan.md).

## Objetivo verificável

Executar os três estudos mínimos com resultados reais e análise de falhas.

## Contratos e decisões

Fatores gravados em `experiments/configs/wave8-protocol.json` antes das
execuções novas. O teste `MOT15-PETS09-S2L1` não escolheu limiar. Contagem
permanece sem anotação de linha. Não se alega significância.

## Critérios de pronto

- [x] A: parâmetros de ByteTrack com detector/dados controlados.
- [x] B: estratos de densidade/oclusão definidos antes da análise.
- [x] C: degradações controladas com GT alinhado, intensidades e seeds explícitos.
- [x] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

A geometria das degradações foi testada sem medir o benchmark. As 30 linhas de
resultado, incluindo o baseline, estão em `experiments/reports/wave8-summary.json`.

## Fora desta tarefa

Fine-tuning, BoT-SORT, superioridade estatística sem suporte e protocolos vazios apresentados como experimentos concluídos.

## Evidências e revisão

Execução local em 2026-10-16, mesmo hardware do baseline, CPU. Comando:
`.venv/bin/python scripts/run_wave8.py`. Durou cerca de 13 minutos e terminou
com 30 linhas. `.venv/bin/pytest -q vision/tests/test_wave8.py`: **3 testes
aprovados**.

### O que foi observado

No teste, `match_thresh` 0,6 levou HOTA de 0,5741 para 0,4455 e ID switches de
30 para 137. Em TUD-Stadtmitte e KITTI-17 o HOTA dessa condição ficou perto do
baseline (0,5927 e 0,5513). `track_buffer` 10 e 60 quase não moveu o HOTA.

Faixas de sequência: KITTI-17 ficou baixa (4,71 objetos/frame); as outras duas
ficaram médias. A faixa alta, a partir de 8, não teve sequência. A faixa de
frame com 9 ou mais objetos também ficou vazia nas três. Oclusão:
`not_evaluated`, porque o MOT15 não traz esse flag. Onde houve frames baixos e
médios, o recall em IoU 0,5 foi maior na faixa baixa (KITTI-17 0,9669 contra
0,8136; PETS09 0,9642 contra 0,9252).

Desfoque sigma 1,5 reduziu o HOTA do teste para 0,4829 e o do KITTI-17 para
0,5190, mas no TUD-Stadtmitte o HOTA foi 0,5974, acima do baseline 0,5913.
CRF 40 reduziu o HOTA nas três. As duas seeds de ruído concordaram dentro de
cada sequência e discordaram entre sequências. Não se escolhe um vencedor.

### Limitações

- Três sequências de pedestres. Sem contagem.
- A faixa alta de densidade ficou vazia. A hipótese de oclusão não foi testada.
- O efeito das degradações muda de sequência. Isso é falha de generalização
  desta amostra, não um efeito único.
- Árvore Git suja durante a execução, como no baseline.

Conclusão: os três estudos têm resultados reais e limitações explícitas.
Próxima ação: Onda 9, sem promover nenhum limiar do teste a padrão.
