# Tarefa: `wave-4-counting`

- Estado: proposed
- Onda: 4 — Linhas, direção e contagem
- Responsável / ferramenta: não atribuído
- Requisitos do escopo: M04, §§12.1, 14
- Dependência: [wave-3-tracking](wave-3-tracking.md), concluída com evidências.
- Arquivos permitidos: vision/geometry/, vision/counting/, vision/contracts/, vision/pipeline/, vision/tests/, examples/, docs/datasets.md, docs/architecture.md. Também este cartão, workboard e ADRs relevantes.
- Plano: [implementation-plan.md — Onda 4](../../implementation-plan.md).

## Objetivo verificável

Produzir contagens exatas em trajetórias sintéticas e eventos auditáveis no vídeo real.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [ ] Segmentos finitos, lados A/B e histerese implementados.
- [ ] Elegibilidade, lacunas e deduplicação por execução/linha/ID/sentido testadas.
- [ ] Eventos por classe/sentido confrontados com pequena anotação manual.
- [ ] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Horizontais/verticais/diagonais, ambos os sentidos, toque, jitter, passagem pela banda, extensão fora do segmento, desaparecimento, lacunas, fora da imagem, duas linhas/classes, retorno e reset.

Os comandos exatos serão registrados após definir os scripts da camada.
Nenhuma validação de implementação foi executada nesta fase documental.

## Fora desta tarefa

Editor web, rearmamento de múltiplas travessias na mesma direção e solução universal para novos IDs.

## Evidências e revisão

Ainda não implementado. Preencher comandos/resultados, diff, artefatos,
checks pulados com motivo, limitações e conclusão da revisão ao executar.
