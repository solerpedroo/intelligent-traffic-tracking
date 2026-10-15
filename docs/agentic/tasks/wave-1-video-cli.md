# Tarefa: `wave-1-video-cli`

- Estado: done
- Onda: 1 — Vídeo, timestamps, CLI e dados
- Responsável / ferramenta: Codex / implementação e revisão sequencial
- Requisitos do escopo: M01, §§6, 11/sprint 1, 17
- Dependência: [wave-0-foundation](wave-0-foundation.md), concluída com evidências.
- Arquivos permitidos: vision/video/, vision/pipeline/, vision/contracts/, vision/tests/, scripts/, examples/, docs/datasets.md, docs/architecture.md, README.md. Também este cartão, workboard e ADRs relevantes. pyproject.toml/uv.lock, CI e estado de AGENTS/plano serão atualizados para instalar/testar o extra de vídeo e registrar o fechamento.
- Plano: [implementation-plan.md — Onda 1](../../implementation-plan.md).

## Objetivo verificável

Ler e exportar vídeo pela CLI com metadados, tempo consistente e dados de avaliação viáveis.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

Decisões técnicas e limites em ADR-007; fonte/plano do piloto em ADR-008.
FramePacket ganhou duration_s opcional compatível com os chamadores da Onda 0.
Instalação básica continua independente; processamento usa extra video.

## Critérios de pronto

- [x] Probe, decode, preview, trecho temporal e export básico.
- [x] Política CFR/VFR/fallback, limites e fechamento de recursos documentados.
- [x] Fontes autorizadas, splits e plano de anotações identificados.
- [x] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Vídeo sintético CFR, VFR quando suportado, entrada vazia/corrompida, decode interrompido, trecho e round-trip. Registrar codec/timestamps observados.

Validação executada com fixtures próprias e codecs reais; comandos abaixo.
Não houve download de vídeos reais ou execução de detector/tracker.

## Fora desta tarefa

YOLO, ByteTrack, upload HTTP e editor web.

## Evidências e revisão

Validação local em 2026-10-15: Fedora Linux, Python 3.12.15 e 3.14.8,
uv 0.13.1, PyAV 18.1.0 e OpenCV headless 4.14.0.94. Executável uv usado
nesta sessão: `/tmp/traffic-uv/uv`; exemplos no README pressupõem uv no PATH.

### Entregas

- `vision/video/`: limites/metadados, probe, decoder PTS/VFR, writer H.264/MP4,
  capacidades reais e erros de domínio. Bibliotecas opcionais no extra video.
- `vision/pipeline/`: serviço reutilizável e CLI instalada `traffic-video`.
- `scripts/generate_sample.py`: fixtures próprias CFR/VFR, sem download.
- `examples/`: limites de exemplo, atribuição das fixtures e plano de cenas.
- `docs/datasets.md`: fonte com licença publicada, três slots por cena e
  protocolo de aquisição, auditoria, splits e anotação. Nada marcado como adquirido.
- CI ampliada para testes reais de vídeo em Python 3.12/3.14, sem pesos/GPU
  ou executáveis FFmpeg do sistema. Estado/arquitetura/README atualizados.

### Comandos e resultados

- `/tmp/traffic-uv/uv sync --locked --extra api --extra video`: aprovado.
- `.venv/bin/ruff check vision backend scripts`: aprovado.
- `.venv/bin/ruff format --check vision backend scripts`: aprovado (27 arquivos).
- `.venv/bin/pytest -q`: **100 testes aprovados** em Python 3.12.15, sem skips.
- `UV_PROJECT_ENVIRONMENT=/tmp/traffic-py314 /tmp/traffic-uv/uv sync --locked --extra api --extra video --python 3.14`
  e `/tmp/traffic-py314/bin/pytest -q`: **100 testes aprovados** em Python 3.14.8.
- `/tmp/traffic-uv/uv build`: wheel e sdist construídos.
- Wheel reinstalado em `/tmp/traffic-core-wave0`, sem API/vídeo: importação
  isolada de contratos/catálogo aprovada; CLI informa `missing_video_extra`
  como JSON/exit 2 em vez de traceback quando falta o extra.
- `/tmp/traffic-uv/uv venv --python 3.12 /tmp/traffic-video-wave1` e instalação
  de `dist/intelligent_traffic_tracking-0.1.0-py3-none-any.whl[video]`: aprovadas.
- Fora do checkout, `/tmp/traffic-video-wave1/bin/traffic-video process /tmp/traffic-wave1-vfr.mp4 --output-dir /tmp/traffic-wave1-installed-output --video-id installed-smoke --start-s 0.12 --end-s 0.61`:
  7 frames exportados, primeiro índice original 2, primeiro tempo original
  0.12 s, timeline exportada a partir de zero, duração final 0.49 s verificada
  por novo decode/probe. Configuração, preview e CSV íntegros.
- `.venv/bin/traffic-video capabilities`: libx264/mpeg4/png disponíveis;
  FFmpeg do PyAV com libavcodec 62.28.102/libavformat 62.12.102.
  Executáveis ffmpeg/ffprobe do sistema ausentes; execução funcionou sem eles.

### Revisão e cenários cobertos

Revisão sequencial Codex: isolamento científico, ordem temporal, memória,
recursos, erros, publicação e documentação. Testes integram codecs reais para
CFR/VFR, offset inicial PTS, limites de recorte, preview exato do frame BGR,
reconciliação de índices/tempo, fonte truncada com header intacto e round-trip.
Há testes de ausência/regressão/duplicação de PTS, EOF vazio, áudio sem vídeo,
limites em headers e decode, corrupção, alteração de geometria, fallback,
CLI, sobrescrita impedida, falha de encoder, interrupção e fechamento de recursos.
Falhas raras são injetadas de forma explícita; não substituem os testes reais.

O teste do MP4 usa tolerância média de 2% da escala de 8 bits devido a conversão
BGR/YUV e compressão lossy, com ordem de canais verificada; PNG usa igualdade
exata. Aritmética de origem PTS foi mantida em frações antes de converter para
float para proteger a inclusão/exclusão de frames nas fronteiras de recorte.

### Limitações e trabalho futuro

- Dados SDD são candidatos planejados, com termos publicados, sem download ou
  auditoria local. Os três slots não são splits congelados ou resultados reais.
  A aquisição e inspeção de câmera/GT devem ocorrer antes do baseline real e
  anotação da Onda 4; termos/atribuição devem acompanhar cada arquivo obtido.
- UA-DETRAC é alternativa identificada, com termos ainda a verificar na origem
  efetivamente obtida; não foi apresentado como dado já autorizado/preparado.
- Pipeline MP4 inicial não normaliza MOV, rotação ou SAR diferente de 1;
  export requer dimensões pares e omite áudio. Preparação de datasets é futura.
- Probe valida headers; recorte não certifica o trecho final que não foi decodificado.
  Quantização de export é 1/90000 s; origem da duração final é registrada.
- Diretórios de saída são novos; erros deixam parciais e failure.json quando
  possível. O summary final é o indicador de conclusão; arquivos isolados não.
- Frontend não foi alterado e não foi revalidado nesta onda; testes backend
  estão incluídos nos 100 checks. CI remota não foi disparada.
- Nenhum benchmark de visão, métricas MOT ou resultado científico foi produzido.

Conclusão: critérios da Onda 1 atendidos localmente, com pendências de aquisição
de dados registradas para as fases correspondentes. Próxima ação: assumir
Onda 2 para integrar detector real e estabelecer baseline de inferência.
