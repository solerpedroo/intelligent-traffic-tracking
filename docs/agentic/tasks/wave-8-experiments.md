# Tarefa: `wave-8-experiments`

- Estado: proposed
- Onda: 8 — Experimentos A/B/C
- Responsável / ferramenta: não atribuído
- Requisitos do escopo: M10, §§10, 14, 16
- Dependência: [wave-7-evaluation](wave-7-evaluation.md), concluída com evidências.
- Arquivos permitidos: experiments/, vision/evaluation/, vision/datasets/, vision/tests/, scripts/, docs/evaluation.md, docs/methodology.md. Também este cartão, workboard e ADRs relevantes.
- Plano: [implementation-plan.md — Onda 8](../../implementation-plan.md).

## Objetivo verificável

Executar os três estudos mínimos com resultados reais e análise de falhas.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [ ] A: parâmetros de ByteTrack com detector/dados controlados.
- [ ] B: estratos de densidade/oclusão definidos antes da análise.
- [ ] C: degradações controladas com GT alinhado, intensidades e seeds explícitos.
- [ ] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Validar configs e transformações temporais; executar CLI com manifests de todas as condições e verificar reprodução. Cada relatório inclui método, resultados por sequência, figuras e limitações.

Os comandos exatos serão registrados após definir os scripts da camada.
Nenhuma validação de implementação foi executada nesta fase documental.

## Fora desta tarefa

Fine-tuning, BoT-SORT, superioridade estatística sem suporte e protocolos vazios apresentados como experimentos concluídos.

## Evidências e revisão

Ainda não implementado. Preencher comandos/resultados, diff, artefatos,
checks pulados com motivo, limitações e conclusão da revisão ao executar.
