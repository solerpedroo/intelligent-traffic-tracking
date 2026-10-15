# Arquitetura — fundação executável

Estado: ondas 0–1. Decisões: [ADRs](agentic/architecture-decisions.md), incluindo
ADR-007 para vídeo e timestamps.
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

Fluxo local existente: CLI → probe → decode sequencial → seleção temporal →
preview/MP4/CSV/JSON. Fluxo futuro: worker → mesmo pipeline → detector → tracker
→ geometria/eventos → exports; API com SQLite e storage local; workspace web.
Não há worker, banco, upload HTTP ou inferência nas ondas 0–1.

## Contratos internos

Pydantic v2 com campos congelados, tipos estritos, números finitos, campos extras
rejeitados e tuplas para coleções. `FramePacket` é dataclass interna: metadados
congelados e array emprestado sem cópia; chamadores não podem alterar os pixels.
Não é payload HTTP/JSON. Frames são BGR `uint8`, H×W×3, contíguos e não vazios.
`duration_s` opcional registra a duração positiva/finita fornecida pelo decoder.

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
--extra api --extra video` instala desenvolvimento, API e vídeo. `uv sync --locked
--no-default-groups` instala só o núcleo. Extras não são persistidos por `uv`;
comandos que sincronizam o ambiente devem incluir os extras `api` e/ou `video` quando necessários.

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

## Pipeline de vídeo da Onda 1

O extra `video` instala PyAV 18.1.0 e OpenCV headless 4.14.0.94 na resolução
registrada no lockfile. PyAV usa suas bibliotecas FFmpeg; os executáveis
ffmpeg/ffprobe do sistema não são necessários. `traffic-video capabilities`
registra versões reais das bibliotecas e disponibilidade dos encoders. A
disponibilidade depende da distribuição instalada; falha de encoder é explícita.

`VideoLimits` e `VideoMetadata` ficam em `vision/video/models.py`. Aceita-se
arquivo local `.mp4`, assinatura ISO-BMFF, codec h264/hevc/mpeg4/av1/vp9 e um
stream de vídeo. O decoder recebe um arquivo aberto; referências externas
MP4 são desabilitadas. Tamanho, duração declarada, pixels e quantidade de frames
são validados antes de processar. Probe é `headers_only`, nunca certificação
de integridade. No decode, limites e geometria são verificados novamente.
Rejeita-se rotação, pixels não quadrados e mudança de dimensões durante a sequência.

`VideoReader` usa apresentação PTS×time_base, não ordem DTS, e subtrai o PTS
do primeiro frame usando frações antes de converter para segundos. Isso evita
perda de precisão ao recortar um stream com offset inicial. CSV e frames mantêm
índice original. PTS ausente, duplicado ou regressivo é erro; `--cfr-fallback-fps`
é uma afirmação explícita do chamador, aplicada à sequência inteira e registrada.
Não se trata o FPS médio de VFR como evidência de cadência fixa. A origem absoluta
fica em `timestamp_origin_s`; em fallback ela é desconhecida (`null`).

O pipeline decodifica desde o início, seleciona `[start_s,end_s)` e conserva
o primeiro frame original como preview PNG. A exportação rebasa o primeiro
frame selecionado para zero. H.264 yuv420p exige dimensões pares, descarta áudio
e usa time base 1/90000; a quantização temporal é de até aproximadamente um tick.
Os intervalos entre frames são preservados. A duração final usa o decoder ou,
se ausente, FPS declarado/25 como fallback de duração, sem mudar os PTS. Essa
origem é registrada no summary; quando há end_s, a duração final é limitada a ele.

A conversão BGR↔YUV e H.264 são lossy; teste sintético usa tolerância média de
2% da escala de 8 bits e verifica ordem de canais, não igualdade de pixels
comprimidos. Preview PNG reproduz exatamente o frame já decodificado.

Memória: um frame corrente no reader e um frame pendente no writer; o encoder
usa um thread, sem B-frames e com zerolatency. Não carregar a sequência inteira.
CSV é incremental e hashing usa blocos de 1 MiB. Context managers fecham arquivos
e codecs, inclusive em cancelamento e falha. Histórico de trajetórias não existe
nesta onda. O writer é uma base de export, sem overlays ou detecção.

Diretório de saída novo impede sobrescrita; CSV, preview e vídeo usam `.partial`
até fechar com sucesso. Summary completo é publicado por último. Erros deixam
`failure.json` quando o disco permite gravá-lo; falta de espaço pode impedir
esse registro, mas não deve mascarar o erro original. Se houver falha durante
a publicação, `failure.json` invalida o conjunto, mesmo com algum arquivo já renomeado.

Validação de um recorte termina no prefixo necessário e não certifica o resto
do vídeo. `summary.input_validation` explicita essa limitação. O throughput
inclui probe/hash/decode/preview/encode/CSV antes da publicação final; FPS de
inferência é `null`. São tempos observados daquela execução, não benchmark YOLO.
