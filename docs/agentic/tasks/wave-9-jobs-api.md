# Tarefa: `wave-9-jobs-api`

- Estado: proposed
- Onda: 9 — API, worker e SQLite
- Responsável / ferramenta: não atribuído
- Requisitos do escopo: §7, M10 e M01 web parcial
- Dependência: [wave-8-experiments](wave-8-experiments.md), concluída com evidências.
- Arquivos permitidos: backend/, vision/pipeline/, vision/contracts/, vision/configs/, arquivos de dependências/lockfiles, .github/workflows/, scripts/, docs/api-contract.md, docs/architecture.md, README.md. Também este cartão, workboard e ADRs relevantes.
- Plano: [implementation-plan.md — Onda 9](../../implementation-plan.md).

## Objetivo verificável

Expor o núcleo por jobs assíncronos persistidos e recuperáveis.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [ ] Rotas do escopo §7.1, criação 202, paginação e erros documentados.
- [ ] Worker separado, claim transacional, progresso, heartbeat, cancelamento e recuperação de crash.
- [ ] Uploads, downloads permitidos, migrações, cotas, retenção e artefatos parciais tratados.
- [ ] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Ciclo HTTP completo, claim concorrente, API reiniciada, worker interrompido/reiniciado, cancelamento queued/running, reprocessamento isolado, disco cheio, path traversal e limpeza com job ativo.

Os comandos exatos serão registrados após definir os scripts da camada.
Nenhuma validação de implementação foi executada nesta fase documental.

## Fora desta tarefa

Inferência dentro de rota, fila distribuída, múltiplos workers e deploy cloud.

## Evidências e revisão

Ainda não implementado. Preencher comandos/resultados, diff, artefatos,
checks pulados com motivo, limitações e conclusão da revisão ao executar.
