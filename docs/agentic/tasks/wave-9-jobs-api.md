# Tarefa: `wave-9-jobs-api`

- Estado: done
- Onda: 9 — API, worker e SQLite
- Responsável / ferramenta: Cursor
- Requisitos do escopo: §7, M10 e M01 web parcial
- Dependência: [wave-8-experiments](wave-8-experiments.md), concluída com evidências.
- Arquivos permitidos: backend/, vision/pipeline/, vision/contracts/, vision/configs/, arquivos de dependências/lockfiles, .github/workflows/, scripts/, docs/api-contract.md, docs/architecture.md, README.md. Também este cartão, workboard e ADRs relevantes. Ampliação: AGENTS, plano e índice dos cartões no encerramento.
- Plano: [implementation-plan.md — Onda 9](../../implementation-plan.md).

## Objetivo verificável

Expor o núcleo por jobs assíncronos persistidos e recuperáveis.

## Contratos e decisões

ADR-015. A rota cria o job e devolve 202. O módulo `backend.app.worker` é quem
chama `process_video`. Cancelamento em execução é consultado a cada frame.
Job interrompido vira `failed` com `worker_interrupted`; outro processamento
ganha outro id.

## Critérios de pronto

- [x] Rotas do escopo §7.1, criação 202, paginação e erros documentados.
- [x] Worker separado, claim transacional, progresso, heartbeat, cancelamento e recuperação de crash.
- [x] Uploads, downloads permitidos, migrações, cotas, retenção e artefatos parciais tratados.
- [x] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Ciclo HTTP com vídeo sintético de 4 frames, claim concorrente, segunda
instância da API no mesmo SQLite, worker interrompido, cancelamento queued e
running, reprocessamento, erro de disco injetado, nome de artefato fora da
lista e limpeza com job ativo.

## Fora desta tarefa

Inferência dentro de rota, fila distribuída, múltiplos workers e deploy cloud.

## Evidências e revisão

Em 2026-10-16, `.venv/bin/ruff check backend` aprovado.
`.venv/bin/pytest -q`: **262 testes aprovados**, 17 deselecionados.
Desses, `backend/tests/test_jobs.py` e `backend/tests/test_health.py` passaram
no ciclo, no claim único, no job interrompido, no cancelamento, no erro de
disco e na limpeza.

O erro de disco foi um `OSError` injetado no processador de teste, não um
disco real cheio. O upload usa corpo binário e `x-filename`, sem
`python-multipart`. A inicialização da API continua sem importar `vision`.

### Limitações

- Um worker e um job ativo.
- Heartbeat é gravado no progresso e no início; a recuperação usa a idade
  desse carimbo.
- Não há fila distribuída.

Conclusão: o ciclo HTTP persiste e o worker publica o summary só ao terminar.
Próxima ação: Onda 10.
