# Tarefa: `wave-0-foundation`

- Estado: proposed
- Onda: 0 — Fundação executável e contratos
- Responsável / ferramenta: não atribuído
- Requisitos do escopo: §§3–4, 9, 12–13
- Dependência: Documentação inicial; nenhuma onda de software anterior.
- Arquivos permitidos: pyproject.toml, lockfiles, backend/, frontend/, vision/contracts/, vision/configs/, vision/tests/, .github/, .gitignore, arquivos de ambiente de exemplo, README.md, docs/architecture.md, docs/api-contract.md. Também este cartão, workboard e ADRs relevantes.
- Plano: [implementation-plan.md — Onda 0](../../implementation-plan.md).

## Objetivo verificável

Criar um monorepo instalável e verificável sem implementar processamento de vídeo.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [ ] Pacote vision, contratos e catálogo inicial sem carregamento de modelos.
- [ ] Shell Next.js, health FastAPI e configuração validada.
- [ ] Lockfiles, checks de qualidade, CI leve e documentação de execução.
- [ ] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Validar contratos, importação independente do núcleo, health e shell. Executar instalação limpa, Ruff/pytest e lint/typecheck/Vitest/build após definir scripts.

Os comandos exatos serão registrados após definir os scripts da camada.
Nenhuma validação de implementação foi executada nesta fase documental.

## Fora desta tarefa

Upload, inferência, tracking, contagem, telas funcionais e infraestrutura cloud.

## Evidências e revisão

Ainda não implementado. Preencher comandos/resultados, diff, artefatos,
checks pulados com motivo, limitações e conclusão da revisão ao executar.
