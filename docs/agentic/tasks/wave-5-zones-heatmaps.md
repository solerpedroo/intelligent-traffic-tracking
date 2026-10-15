# Tarefa: `wave-5-zones-heatmaps`

- Estado: proposed
- Onda: 5 — ROI, permanência e heatmaps
- Responsável / ferramenta: não atribuído
- Requisitos do escopo: M05–M06
- Dependência: [wave-4-counting](wave-4-counting.md), concluída com evidências.
- Arquivos permitidos: vision/geometry/, vision/analytics/, vision/contracts/, vision/pipeline/, vision/rendering/, vision/tests/, docs/architecture.md. Também este cartão, workboard e ADRs relevantes.
- Plano: [implementation-plan.md — Onda 5](../../implementation-plan.md).

## Objetivo verificável

Medir ocupação baseada em tracks e visualizar densidade de observações.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [ ] ROI inclui borda e rejeita polígonos inválidos.
- [ ] Presença, perda, entrada/saída e dwell com censura explícita.
- [ ] Heatmaps por classe/janela com parâmetros e unidades registrados.
- [ ] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Borda/vértice, zonas sobrepostas, entrada/saída, perda, início/fim dentro da zona, timestamps irregulares e acumulação conhecida de heatmap.

Os comandos exatos serão registrados após definir os scripts da camada.
Nenhuma validação de implementação foi executada nesta fase documental.

## Fora desta tarefa

Densidade física por metro quadrado, velocidade real e inferência automática de congestionamento.

## Evidências e revisão

Ainda não implementado. Preencher comandos/resultados, diff, artefatos,
checks pulados com motivo, limitações e conclusão da revisão ao executar.
