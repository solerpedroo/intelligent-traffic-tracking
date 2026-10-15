# Arquitetura — fundação executável

Estado: Onda 0. Decisões: [ADR-003, ADR-004 e ADR-006](agentic/architecture-decisions.md).
Escopo futuro: [plano de implementação](implementation-plan.md).

## Componentes existentes

- `vision/`: pacote científico, com contratos e catálogo JSON empacotado.
  Instalação básica requer NumPy e Pydantic, sem dependências HTTP ou de modelos.
- `backend.app`: extra Python `api`; factory `create_app(settings)` e instância
  ASGI `app`, configuração validada e uma rota de liveness.
- `frontend/`: Next.js App Router, TypeScript e shell em inglês. Apenas o
  indicador de health é um Client Component; página/layout são Server Components.
  Sem fontes, imagens ou serviços externos exigidos durante o build.

Fluxo atual: navegador → cliente `fetchHealth` → FastAPI `/api/health` →
validação do payload na fronteira TypeScript → indicador acessível no shell.
API indisponível não impede renderizar a página. O cliente tem timeout de cinco
segundos e aborta a requisição ao desmontar. O build não depende da API ativa.

Fluxo futuro, ainda não implementado: CLI/worker → decode → detector → tracker
→ geometria/eventos → exports; API com SQLite e storage local; workspace web.
Não há worker, banco, upload, inferência ou processamento de vídeo nesta onda.

## Contratos internos

Pydantic v2 com campos congelados, tipos estritos, números finitos, campos extras
rejeitados e tuplas para coleções. `FramePacket` é dataclass interna: metadados
congelados e array emprestado sem cópia; chamadores não podem alterar os pixels.
Não é payload HTTP/JSON. Frames são BGR `uint8`, H×W×3, contíguos e não vazios.

`Detection`/`Track` usam boxes xyxy em pixels originais com largura/altura
positivas; boxes fora da imagem não são cortadas silenciosamente. Adapters
validarão limites contra as dimensões reais. Confidence em `[0,1]`, IDs inteiros
não negativos; `observed`, `predicted` e `lost` são estados distintos.

`TrackObservation`, `CrossingEvent` e `ZoneEvent` carregam run/video, índice
original e segundos da mídia. `A_TO_B`/`B_TO_A` seguem ADR-004. Zona diferencia
saída geométrica, perda de observação e censura na fronteira temporal.
Nenhum desses contratos implementa os respectivos algoritmos.

`ProcessingConfig` v1.0 fixa stride 1, trecho válido e referências opcionais a
modelo/tracker. `None` significa não configurado; não há modelo implicitamente
disponível. Thresholds, geometrias e validação de disponibilidade entram com os
adapters das ondas responsáveis. Alterações incompatíveis exigem nova versão;
expansões futuras precisam documentar compatibilidade/migração.

`RunManifest` registra configuração, SHA-256 da entrada, horário com timezone,
estado Git, seed opcional, hardware, versões e referência de checkpoint quando
disponível. A referência deve concordar com o modelo configurado. O manifest
completo de execução será ampliado na Onda 6. `RunProgress` valida snapshots,
incluindo totais desconhecidos; transições/persistência entram na Onda 9.

## Catálogo

`vision/configs/catalog.json` é carregado por `importlib.resources`, também
quando instalado a partir de wheel fora do repositório. Modelos e presets
estão vazios. O loader não acessa rede, não baixa pesos nem importa frameworks.
O schema será expandido quando houver um adapter real; não há endpoint de
catálogo nesta onda.

## Ambiente e ferramentas

Baseline Python 3.12; compatibilidade da fundação testada também em 3.14.
Isso não garante compatibilidade futura de YOLO/PyTorch em ambas as versões;
a Onda 2 deve validar essa matriz. `uv.lock` fixa a resolução; `uv sync --locked
--extra api` instala o ambiente de desenvolvimento e a API. `uv sync --locked
--no-default-groups` instala só o núcleo. Extras não são persistidos por `uv`;
comandos que sincronizam o ambiente devem incluir `--extra api` quando necessário.

Node 24 e npm, com dependências diretas exatas e lockfile. Biome faz lint,
formatação e organização de imports; TypeScript valida tipos; Vitest/jsdom
testam o cliente e o shell. Playwright de produto começa quando houver fluxo web.
Ruff faz lint/formatação Python; pytest cobre contratos, ASGI, CORS e isolamento.

CI executa os mesmos checks em Python 3.12/3.14, constrói wheel/sdist e testa o
wheel em ambiente sem API. Frontend passa por `npm ci`, lint, tipos, testes e
build. Actions são fixadas por commit. Não há downloads de pesos, vídeos ou GPU.

## Configuração

`Settings` lê `TRAFFIC_ALLOWED_ORIGINS` como array JSON e `TRAFFIC_LOG_LEVEL`
como nível permitido. Por padrão, apenas origins locais na porta 3000.
CORS não é autenticação. O servidor de desenvolvimento deve escutar em loopback.
`.env` é carregado explicitamente pelo Uvicorn com `--env-file .env`.

`NEXT_PUBLIC_API_URL` é um origin HTTP(S), sem caminho, credenciais, query ou
fragmento. Valor público incorporado ao bundle no build; alterar exige rebuild.
`.env.local` do Next.js pode ser criado a partir de `frontend/.env.example`.
Nenhuma configuração de segredo é necessária na fundação.
