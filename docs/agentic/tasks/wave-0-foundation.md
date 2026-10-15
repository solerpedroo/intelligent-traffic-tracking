# Tarefa: `wave-0-foundation`

- Estado: done
- Onda: 0 — Fundação executável e contratos
- Responsável / ferramenta: Codex / implementação e revisão sequencial
- Requisitos do escopo: §§3–4, 9, 12–13
- Dependência: Documentação inicial; nenhuma onda de software anterior.
- Arquivos permitidos: pyproject.toml, .python-version, lockfiles, backend/, frontend/, vision/__init__.py, vision/contracts/, vision/configs/, vision/tests/, .github/, .gitignore, arquivos de ambiente de exemplo, README.md, docs/architecture.md, docs/api-contract.md. Também este cartão, workboard e ADRs relevantes. Atualizações de estado em AGENTS.md e implementation-plan.md são parte do encerramento documental.
- Plano: [implementation-plan.md — Onda 0](../../implementation-plan.md).

## Objetivo verificável

Criar um monorepo instalável e verificável sem implementar processamento de vídeo.

## Contratos e decisões

Contratos afetados: frames, detecções, tracks/observações, eventos, configuração,
manifest, progresso e catálogo. API restrita ao health; UI restrita ao shell.
Python 3.12 como baseline, uv/uv.lock, Node 24 e npm/package-lock.json.
Escolhas registradas em ADR-006 antes da implementação.

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [x] Pacote vision, contratos e catálogo inicial sem carregamento de modelos.
- [x] Shell Next.js, health FastAPI e configuração validada.
- [x] Lockfiles, checks de qualidade, CI leve e documentação de execução.
- [x] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Validar contratos, importação independente do núcleo, health e shell. Executar instalação limpa, Ruff/pytest e lint/typecheck/Vitest/build após definir scripts.

Comandos e resultados reais registrados abaixo. Não houve processamento de vídeo,
inferência ou downloads de dados/pesos nesta onda.

## Fora desta tarefa

Upload, inferência, tracking, contagem, telas funcionais e infraestrutura cloud.

## Evidências e revisão

Verificação local em 2026-10-15, Fedora Linux, Node 24.21.0, npm 11.19.0,
uv 0.13.1, Python 3.12.15 e 3.14.8. uv foi usado a partir de
`/tmp/traffic-uv/uv`; no README, `uv` pressupõe instalação no PATH.

### Comandos executados

- `/tmp/traffic-uv/uv sync --locked --extra api`: ambiente instalável a partir do lock.
- `.venv/bin/ruff check vision backend`: aprovado.
- `.venv/bin/ruff format --check vision backend`: 16 arquivos formatados.
- `.venv/bin/pytest -q`: **60 testes aprovados** em Python 3.12.15.
- `UV_PROJECT_ENVIRONMENT=/tmp/traffic-py314 /tmp/traffic-uv/uv sync --locked --extra api --python 3.14`
  e `/tmp/traffic-py314/bin/pytest -q`: **60 testes aprovados** em Python 3.14.8.
- `/tmp/traffic-uv/uv build`: sdist e wheel construídos.
- `/tmp/traffic-uv/uv venv --python 3.12 /tmp/traffic-core-wave0` e
  `/tmp/traffic-uv/uv pip install --python /tmp/traffic-core-wave0/bin/python dist/intelligent_traffic_tracking-0.1.0-py3-none-any.whl`:
  instalação limpa do wheel; importação isolada fora do repositório comprovou
  contratos/catálogo e ausência de FastAPI, Uvicorn, OpenCV e PyTorch.
- Em `frontend/`: `npm ci`, `npm run lint`, `npm run typecheck`,
  `npm run test` (**10 testes persistentes**) e `npm run build`: aprovados.
- `npm ci`: **zero vulnerabilidades reportadas** nas 124 entradas auditadas.
- Smoke adicional temporário React/jsdom consultando a API real, sem mock:
  **1 teste aprovado**, indicador `API available`. Arquivo temporário removido;
  não é teste persistente da CI, que não requer servidor iniciado.
- `.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`:
  API iniciou sem biblioteca científica/modelo; `/api/health` respondeu 200.
- `npm run start` e `curl -fsS http://127.0.0.1:3000`: shell de produção 200,
  HTML em inglês, heading e estado inicial de health presentes.
- Cliente real `fetchHealth` executado por Node retornou o payload esperado;
  OpenAPI lista apenas `/api/health` como rota de produto.

### Revisão

Revisão sequencial pelo Codex: fronteiras, tipos estritos, finitude, reset futuro,
serialização, estados ausentes, catálogo empacotado, CORS e dependências opcionais.
A API não importa o núcleo; o núcleo não importa transporte ou modelos.
`FramePacket` preserva buffer emprestado e deixa essa mutabilidade explícita.
Configurações/modelos/algoritmos de ondas futuras não foram simulados como prontos.

Foram corrigidas durante a validação: compatibilidade do TestClient com httpx2,
dependência de lint com advisory transitivo (substituída por Biome) e geração de
tipos Next.js antes de typecheck em checkout limpo. Uma requisição ao frontend
retornou 500 enquanto `npm ci` recriava node_modules com o servidor ativo; após
concluir a instalação e reiniciar o servidor, o smoke de produção retornou 200.

### Limitações e verificações não executadas

- Workflow GitHub Actions criado com Actions fixadas por commit; os checks foram
  executados localmente. Execução remota não foi disparada nesta sessão.
- Browser/inspeção visual indisponível: a ferramenta de browser retornou inventário
  vazio. Validação foi feita por HTTP, cliente real e React/jsdom; não alegar E2E
  em navegador real. Playwright do fluxo de produto continua na Onda 10.
- Não há benchmark, dados, pesos, decode, tracker, persistência ou worker nesta onda.
- Artefatos de build e ambientes locais estão ignorados pelo Git.

Conclusão: critérios executáveis da fundação verificados localmente, sem bloqueador
identificado na revisão. CI remota e inspeção visual não foram apresentadas como
aprovadas. Próxima ação: assumir o cartão da Onda 1, sem iniciá-la automaticamente.
