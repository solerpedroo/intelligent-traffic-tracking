# Tarefa: `wave-12-acceptance`

- Estado: done
- Onda: 12 — Aceitação e portfólio
- Responsável / ferramenta: Cursor, com teste manual no navegador
- Requisitos do escopo: §§12–15, 17
- Dependência: [wave-11-analytics](wave-11-analytics.md), concluída com evidências.
- Arquivos permitidos: README.md, docs/, examples/, scripts/, .github/, arquivos de licença/inventário, frontend/ e testes, backend/ e testes, vision/ e testes; correções delimitadas em cartões próprios. Também este cartão, workboard e ADRs relevantes.
- Plano: [implementation-plan.md — Onda 12](../../implementation-plan.md).

## Objetivo verificável

Comprovar o MVP em uso local e registrar a demonstração sem inventar licença
nem versionar vídeo de terceiro.

## Contratos e decisões

O mapa está em [mvp-acceptance.md](../../mvp-acceptance.md). Não há ADR novo
nem arquivo `LICENSE`.

## Critérios de pronto

- [x] Aceitação dos 14 critérios com referências a testes/artefatos reais.
- [x] Regressão e ensaio local de 1192 frames, com disco medido.
- [x] README em inglês e termos revisados. O vídeo de demonstração existe só em `data/`.
- [x] Validação executada, documentação atualizada e revisão registrada.

## Fora desta tarefa

Deploy automático, features P2 e fechamento com apenas storyboard ou experimentos não executados.

## Evidências e revisão

Regressão Python após o timeout de 30 s do SQLite: **266 testes aprovados**,
17 deselecionados. Frontend: lint, **25 testes** e typecheck. Playwright e
build não foram repetidos nesta sessão.

Teste manual em 2026-10-16: upload aceito (`201`) do arquivo de 1920×1080 e
47,68 s; preview `200`; job `777c59836493467fb9912988b1e147a7` em `202` e
depois `completed`, com 1192 frames, MP4 publicado e leitura `206` no
navegador. Tempos e disco estão no mapa de aceitação. Três uploads anteriores
voltaram `422` antes desse arquivo aceito.

### Limitações

- O job local não incluiu linhas de contagem.
- RSS e clone limpo não foram medidos.
- O MP4 não entra no git. Não há `LICENSE`.

Conclusão: o fluxo local de upload, inferência CPU e vídeo anotado foi
observado. A licença do repositório continua sem escolha.
