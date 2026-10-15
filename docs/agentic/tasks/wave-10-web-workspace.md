# Tarefa: `wave-10-web-workspace`

- Estado: proposed
- Onda: 10 — Workspace, editor e viewer
- Responsável / ferramenta: não atribuído
- Requisitos do escopo: §8, M01/M04/M05/M07 web
- Dependência: [wave-9-jobs-api](wave-9-jobs-api.md), concluída com evidências.
- Arquivos permitidos: frontend/, backend/app/api/, backend/app/schemas/, backend/tests/, examples/, .github/workflows/, docs/api-contract.md, README.md. Também este cartão, workboard e ADRs relevantes.
- Plano: [implementation-plan.md — Onda 10](../../implementation-plan.md).

## Objetivo verificável

Concluir upload, geometria, execução e inspeção pelo navegador.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [ ] Overview, Workspace, Jobs e Viewer com catálogo/cliente tipado.
- [ ] Editor normalizado com direção, linhas/zonas, resize/letterboxing e alternativa por campos.
- [ ] Polling terminal, cancelamento, erros recuperáveis, vídeo e downloads acessíveis.
- [ ] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Vitest para transformações do editor e estados; Playwright upload→linha→job→resultado→download; smoke local com núcleo real separado das fixtures leves da CI.

Os comandos exatos serão registrados após definir os scripts da camada.
Nenhuma validação de implementação foi executada nesta fase documental.

## Fora desta tarefa

Duplicação de contadores no frontend e analytics avançado da próxima onda.

## Evidências e revisão

Ainda não implementado. Preencher comandos/resultados, diff, artefatos,
checks pulados com motivo, limitações e conclusão da revisão ao executar.
