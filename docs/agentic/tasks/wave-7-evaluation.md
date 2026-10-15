# Tarefa: `wave-7-evaluation`

- Estado: proposed
- Onda: 7 — Avaliação e benchmark
- Responsável / ferramenta: não atribuído
- Requisitos do escopo: M09, §§6, 10.1, 12.4
- Dependência: [wave-6-exports](wave-6-exports.md), concluída com evidências.
- Arquivos permitidos: vision/evaluation/, vision/datasets/, vision/tests/, experiments/configs/, experiments/reports/, scripts/, docs/datasets.md, docs/evaluation.md, docs/methodology.md, arquivos de dependências/lockfiles. Também este cartão, workboard e ADRs relevantes.
- Plano: [implementation-plan.md — Onda 7](../../implementation-plan.md).

## Objetivo verificável

Medir o baseline com referências válidas e protocolo congelado.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [ ] Conversores GT e TrackEval validados sem erro de indexação.
- [ ] Detecção, MOT, contagem/eventos e desempenho avaliados separadamente.
- [ ] Resultados reais por sequência, agregações e limitações reproduzíveis.
- [ ] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Referências perfeitas e erros conhecidos, frames/IDs, classes ignoradas, tolerância temporal, pareamento um a um, GT zero e denominadores vazios; executar benchmark real.

Os comandos exatos serão registrados após definir os scripts da camada.
Nenhuma validação de implementação foi executada nesta fase documental.

## Fora desta tarefa

Métricas calculadas de GT inexistente, metas inventadas e ajuste de parâmetros no teste.

## Evidências e revisão

Ainda não implementado. Preencher comandos/resultados, diff, artefatos,
checks pulados com motivo, limitações e conclusão da revisão ao executar.
