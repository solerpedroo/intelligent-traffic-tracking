# Tarefa: `wave-1-video-cli`

- Estado: proposed
- Onda: 1 — Vídeo, timestamps, CLI e dados
- Responsável / ferramenta: não atribuído
- Requisitos do escopo: M01, §§6, 11/sprint 1, 17
- Dependência: [wave-0-foundation](wave-0-foundation.md), concluída com evidências.
- Arquivos permitidos: vision/video/, vision/pipeline/, vision/contracts/, vision/tests/, scripts/, examples/, docs/datasets.md, docs/architecture.md, README.md. Também este cartão, workboard e ADRs relevantes.
- Plano: [implementation-plan.md — Onda 1](../../implementation-plan.md).

## Objetivo verificável

Ler e exportar vídeo pela CLI com metadados, tempo consistente e dados de avaliação viáveis.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [ ] Probe, decode, preview, trecho temporal e export básico.
- [ ] Política CFR/VFR/fallback, limites e fechamento de recursos documentados.
- [ ] Fontes autorizadas, splits e plano de anotações identificados.
- [ ] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Vídeo sintético CFR, VFR quando suportado, entrada vazia/corrompida, decode interrompido, trecho e round-trip. Registrar codec/timestamps observados.

Os comandos exatos serão registrados após definir os scripts da camada.
Nenhuma validação de implementação foi executada nesta fase documental.

## Fora desta tarefa

YOLO, ByteTrack, upload HTTP e editor web.

## Evidências e revisão

Ainda não implementado. Preencher comandos/resultados, diff, artefatos,
checks pulados com motivo, limitações e conclusão da revisão ao executar.
