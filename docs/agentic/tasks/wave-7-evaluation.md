# Tarefa: `wave-7-evaluation`

- Estado: blocked
- Onda: 7 — Avaliação e benchmark
- Responsável / ferramenta: Cursor
- Requisitos do escopo: M09, §§6, 10.1, 12.4
- Dependência: [wave-6-exports](wave-6-exports.md), concluída com evidências.
- Arquivos permitidos: vision/evaluation/, vision/datasets/, vision/tests/, experiments/configs/, experiments/reports/, scripts/, docs/datasets.md, docs/evaluation.md, docs/methodology.md, arquivos de dependências/lockfiles. Também este cartão, workboard e ADRs relevantes. Ampliação: AGENTS, README, plano e índice dos cartões para registrar o bloqueio.
- Plano: [implementation-plan.md — Onda 7](../../implementation-plan.md).
- Bloqueio: splits reais não auditados. `experiments/configs/splits.json` tem `test_split_frozen: false` e SHA-256 nulo. Sem sequência externa congelada não há baseline para fechar a onda.

## Objetivo verificável

Medir o baseline com referências válidas e protocolo congelado.

## Contratos e decisões

Contratos afetados: ground truth canônico, protocolo 1.0 e relatório por
sequência. Decisão em ADR-014. O protocolo numérico foi congelado antes de
qualquer score externo. O split de teste não foi congelado.

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [x] Conversores GT e TrackEval validados sem erro de indexação.
- [x] Detecção, MOT, contagem/eventos e desempenho avaliados separadamente.
- [ ] Resultados reais por sequência, agregações e limitações reproduzíveis.
- [x] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Referências perfeitas e erros conhecidos, frames/IDs, classes ignoradas, tolerância temporal, pareamento um a um, GT zero e denominadores vazios; executar benchmark real.

O benchmark real não foi executado. O motivo está no bloqueio acima.

## Fora desta tarefa

Métricas calculadas de GT inexistente, metas inventadas e ajuste de parâmetros no teste.

## Evidências e revisão

Verificação local em 2026-10-15, Python 3.12.15. Nenhum vídeo ou peso novo foi
baixado. O extra `evaluation` foi sincronizado só para o teste TrackEval.

### Comandos executados

- `.venv/bin/ruff check vision backend scripts`: aprovado.
- `.venv/bin/ruff format --check vision backend scripts`: 78 arquivos já formatados.
- `.venv/bin/pytest -q`: **251 testes aprovados**, 17 deselecionados.
- `.venv/bin/pytest -q -m evaluation`: **1 teste aprovado**, 267 deselecionados.
- `.venv/bin/pytest -q -m tracker`: **13 testes aprovados**, depois de restaurar
  o OpenCV headless 4.14.0.94.

### Oráculo sintético observado

TrackEval 1.3.0, duas caixas idênticas em frames 0 e 1, classe 2:

- predição com o mesmo id: HOTA 1.0, MOTA 1.0, IDF1 1.0, IDSW 0
- troca de id no segundo frame: HOTA 0.7071067811865476, MOTA 0.5, IDF1 0.5, IDSW 1

O conversor grava esses frames como 1 e, quando há buraco, preserva o índice
seguinte. IoU 0,6 conhecido produz mAP@50:95 0,3. Contagem com ground truth
zero guarda erro absoluto e deixa o relativo nulo. A CLI sem
`--allow-development` sai com código 2 e não cria relatório.

### Revisão

Detecção, eventos, desempenho e MOT não preenchem métrica ausente com zero.
A média agregada também ignora `not_evaluated`. O pacote TrackEval publicado
depende de `opencv-python` 5; essa dependência foi retirada do metadado
resolvido para não substituir o `cv2` headless do extra `video`. O import do
BURST dentro do TrackEval pede `pycocotools`, que não é necessário para HOTA
em caixas e não foi instalado. A saída desse aviso é descartada.

### Limitações

- Em 2026-10-15 a página oficial ainda aponta
  `http://vatic2.stanford.edu/stanford_campus_dataset.zip` (~69 GB, CC BY-NC-SA 3.0).
  O host resolve para 171.64.68.58, mas HTTP e HTTPS expiraram sem resposta
  (20 s e 15 s). Não houve arquivo, hash, auditoria de câmera nem relatório real.
- Não há resultado por sequência real, nem agregação de teste congelado.
- RAM e VRAM não são medidas.
- O piloto `vehicles.mp4` não foi reprocessado e continua fora do benchmark.
- CI remota não foi disparada. O job leve não instala o extra `evaluation`.

Conclusão: ferramentas e protocolo estão verificados. A onda permanece
bloqueada até a auditoria e o congelamento dos splits. Não iniciar a Onda 8.
