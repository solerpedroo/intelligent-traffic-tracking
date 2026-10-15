# Tarefa: `wave-2-detection`

- Estado: proposed
- Onda: 2 — Detector YOLO e baseline
- Responsável / ferramenta: não atribuído
- Requisitos do escopo: M02, §§3, 17
- Dependência: [wave-1-video-cli](wave-1-video-cli.md), concluída com evidências.
- Arquivos permitidos: vision/detectors/, vision/configs/, vision/pipeline/, vision/rendering/, vision/tests/, arquivos de dependências/lockfiles, docs/architecture.md, README.md. Também este cartão, workboard e ADRs relevantes.
- Plano: [implementation-plan.md — Onda 2](../../implementation-plan.md).

## Objetivo verificável

Integrar detector real e renderizar classes/boxes nas coordenadas originais.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [ ] Checkpoint/versionamento/hash e class mapping registrados.
- [ ] Adapter, thresholds e inversão de resize/letterbox testados.
- [ ] Smoke real CPU, manifest e timings separados.
- [ ] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Boxes em múltiplas proporções, classes inválidas, saída vazia e smoke com checkpoint real. Registrar preparação de pesos e separar esse teste da CI leve.

Os comandos exatos serão registrados após definir os scripts da camada.
Nenhuma validação de implementação foi executada nesta fase documental.

## Fora desta tarefa

Tracking, fine-tuning, metas de FPS e comparação de modelos sem protocolo.

## Evidências e revisão

Ainda não implementado. Preencher comandos/resultados, diff, artefatos,
checks pulados com motivo, limitações e conclusão da revisão ao executar.
