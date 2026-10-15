# Tarefa: `wave-6-exports`

- Estado: proposed
- Onda: 6 — Exports e integridade do núcleo
- Responsável / ferramenta: não atribuído
- Requisitos do escopo: M07, M10, P0
- Dependência: [wave-5-zones-heatmaps](wave-5-zones-heatmaps.md), concluída com evidências.
- Arquivos permitidos: vision/pipeline/, vision/rendering/, vision/analytics/, vision/contracts/, vision/tests/, examples/sample_results/, docs/architecture.md, README.md. Também este cartão, workboard e ADRs relevantes.
- Plano: [implementation-plan.md — Onda 6](../../implementation-plan.md).

## Objetivo verificável

Consolidar artefatos reproduzíveis sem perder resultados numéricos por falha de vídeo.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [ ] CSV de eventos/tracks/zonas, summary, config e manifest versionados.
- [ ] Vídeo com IDs, linhas, zonas, rastros e contadores.
- [ ] Escrita final atômica, parciais explícitos e reprodução pela configuração.
- [ ] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Pipeline curto completo, exports vazios, reconciliação eventos-summary, schemas, falha de codec, interrupção de escrita e reexecução da configuração.

Os comandos exatos serão registrados após definir os scripts da camada.
Nenhuma validação de implementação foi executada nesta fase documental.

## Fora desta tarefa

API de jobs, dashboard e resultados de benchmarks ainda não executados.

## Evidências e revisão

Ainda não implementado. Preencher comandos/resultados, diff, artefatos,
checks pulados com motivo, limitações e conclusão da revisão ao executar.
