# Tarefa: `wave-3-tracking`

- Estado: proposed
- Onda: 3 — ByteTrack e trajetórias
- Responsável / ferramenta: não atribuído
- Requisitos do escopo: M03 e M06 parcial
- Dependência: [wave-2-detection](wave-2-detection.md), concluída com evidências.
- Arquivos permitidos: vision/trackers/, vision/configs/, vision/contracts/, vision/pipeline/, vision/rendering/, vision/tests/, arquivos de dependências/lockfiles, docs/architecture.md. Também este cartão, workboard e ADRs relevantes.
- Plano: [implementation-plan.md — Onda 3](../../implementation-plan.md).

## Objetivo verificável

Associar detecções temporalmente com estado isolado e trajetórias persistidas.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [ ] Implementação concreta de ByteTrack e compatibilidade de thresholds registradas.
- [ ] Reset, frames vazios, política de classe e unidade de buffer definidos.
- [ ] Rastros limitados em RAM e trajetórias completas em streaming.
- [ ] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Usar tracker real com sequências controladas: continuidade, oclusão curta, baixa confiança, buffer, frames vazios e reset. Sem GT não afirmar ID switches confirmados.

Os comandos exatos serão registrados após definir os scripts da camada.
Nenhuma validação de implementação foi executada nesta fase documental.

## Fora desta tarefa

Reidentificação persistente, novo tracker e métricas MOT sem referência.

## Evidências e revisão

Ainda não implementado. Preencher comandos/resultados, diff, artefatos,
checks pulados com motivo, limitações e conclusão da revisão ao executar.
