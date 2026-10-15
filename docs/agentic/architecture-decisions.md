# Decisões arquiteturais

Este registro distingue diretrizes aceitas de escolhas ainda pendentes.
Aceitação documental não significa implementação. Novas entradas usam ID,
data, estado, contexto, decisão e consequências; ao substituir uma decisão,
referenciar a anterior sem apagar seu histórico.

## ADR-001 — Contexto compartilhado e entrega por ondas

- Data: 2026-10-15. Estado: aceito para planejamento.
- Contexto: desenvolvimento alternado em Cursor e Codex, baseado no protocolo
  do projeto `computer-vision-processing-lab`.
- Decisão: AGENTS, plano, cartões, workboard, ADRs e handoffs são o contexto
  durável. Papéis podem ser exercidos por um único agente sequencialmente.
- Consequência: nenhuma onda de código é concluída por existir sua documentação.

## ADR-002 — Núcleo → avaliação → web

- Data: 2026-10-15. Estado: aceito para planejamento.
- Contexto: há divergência de ordem entre as seções 11 e 20 do escopo.
- Decisão: seguir a orientação final da seção 20, avaliando o baseline e
  realizando os experimentos mínimos antes da aplicação web completa.
- Consequência: ondas 0–6 núcleo; 7–8 ciência; 9–11 produto; 12 aceitação.
  O scaffold web inicial não antecipa features de interface.

## ADR-003 — Isolamento científico e execução local

- Data: 2026-10-15. Estado: aceito para planejamento, conforme escopo §§4 e 17.
- Decisão: `vision/` independente de HTTP; CLI e worker compartilham pipeline.
  FastAPI e worker são processos distintos, SQLite e filesystem no MVP,
  um worker com um job ativo; CPU funcional, GPU opcional.
- Consequência: infraestrutura cloud, filas distribuídas e novo storage não são
  pré-requisitos; troca futura não pode exigir reescrever os contadores.

## ADR-004 — Geometria, tempo e identidade

- Data: 2026-10-15. Estado: aceito para planejamento.
- Decisão: BGR uint8 no decode; boxes xyxy em pixels originais; geometria
  normalizada; frames zero-based e tempo da mídia original. IDs locais à
  execução; `run_id` identifica a CLI e mapeia para `job_id` na API.
  Linha orientada tem A negativo/B positivo pelo produto vetorial; ROI inclui
  borda. Crossing considera segmento finito e deduplica por execução/linha/ID/sentido.
- Consequência: testes de coordenadas e direção precedem editor web. A fonte
  concreta de PTS/VFR e tratamento de lacunas serão registrados na Onda 1.

## ADR-005 — Evidência científica e experimentos mínimos

- Data: 2026-10-15. Estado: aceito para planejamento.
- Contexto: robustez aparece como P2, mas três experimentos são exigidos no MVP.
- Decisão: executar A/B/C mínimos conforme critérios do escopo; expansões,
  fine-tuning e BoT-SORT ficam após baseline. MOT exige GT de IDs, contagem
  exige referência própria; métricas ausentes recebem motivo, nunca valor fictício.
- Consequência: seleção de dados começa na Onda 1; metas quantitativas surgem
  após medições, sem promessa antecipada de HOTA, IDF1 ou FPS.

## Decisões pendentes

- Onda 0: resolvido por ADR-006; versões exatas nos lockfiles.
- Onda 1: implementação técnica resolvida por ADR-007 e plano de dados por ADR-008;
  aquisição/auditoria e congelamento dos splits reais seguem pendentes antes da avaliação.
- Onda 2: checkpoint/contrato resolvidos por ADR-009. Onda 3 ainda deve
  definir ByteTrack concreto, alinhar thresholds e estabilizar classe da track.
- Ondas 4–5: tamanho mínimo, banda, lacuna máxima e regras temporais de dwell.
- Onda 7: formatos GT, tolerâncias de pareamento e agregações científicas.
- Onda 9: migrações, retenção/cotas, heartbeat, recuperação e contrato HTTP final.
- Onda 12: LICENSE e eventual plano de hospedagem, após verificar termos reais.

## ADR-006 — Toolchain e contratos da fundação

- Data: 2026-10-15. Estado: aceito para implementação da Onda 0.
- Decisão: baseline Python 3.12 (compatibilidade com o ecossistema científico),
  uv e uv.lock; Node 24 LTS, npm e package-lock.json. Pacote raiz instala
  `vision`; extra `api` instala o backend, sem acoplar o núcleo ao FastAPI.
- Frontend usa Biome para lint/formatação, TypeScript e Vitest.
- Contratos usam Pydantic v2 congelado, campos extras rejeitados e números
  finitos; NumPy somente para o contrato de frame. Frames são objetos internos
  não serializáveis em JSON; snapshots de configuração usam coleções imutáveis.
- Catálogo JSON empacotado começa vazio; nenhum ID/checkpoint fictício. Health
  indica liveness do serviço, não disponibilidade de modelos ou worker.
- Configuração do servidor via TRAFFIC_*; CORS explícito e restrito aos origins
  locais por padrão. Cliente futuro usa NEXT_PUBLIC_API_URL, validada em sua fronteira.
- Consequência: CI testa Python 3.12 e 3.14, instalação do núcleo sem extras API,
  API com health e shell Next.js. Modelos, vídeo, persistência e filas entram
  somente nas ondas responsáveis. Hashes/versões exatas ficam nos lockfiles.

### Evidência de compatibilidade da toolchain

O ambiente inicial possui Python 3.14 e Node 24; uv provisionou Python 3.12
sem alterar o Python do sistema. O cliente de testes exigido pelo Starlette
resolvido é httpx2; a dependência de desenvolvimento acompanha essa API.
Biome substitui o conjunto ESLint/Next que trouxe um advisory transitivo sem
correção disponível na versão consultada. Não se usa override incompatível
nem se ignora esse advisory. O contrato de checks (lint, tipos, testes e build)
permanece o mesmo. Referências: [Next.js](https://nextjs.org/docs/app/getting-started/installation),
[uv](https://docs.astral.sh/uv/concepts/projects/sync/),
[Biome](https://biomejs.dev/installation/quick-start/).

## ADR-007 — Entrada de vídeo e tempo da mídia (Onda 1)

- Data: 2026-10-15. Estado: aceito para implementação.
- Decisão: extra `video` instala PyAV (FFmpeg) para probe/decode/encode e
  OpenCV headless para preview PNG. Não exigir executáveis ffmpeg/ffprobe do
  sistema; registrar bibliotecas efetivamente usadas e encoders disponíveis.
- Entrada inicial: arquivo local MP4/ISO-BMFF, exatamente um stream de vídeo,
  codec permitido, pixels quadrados, sem rotação. Não aceitar URLs, playlists
  ou sequências de imagens implicitamente. Áudio não é copiado na exportação.
- Limites padrão configuráveis por JSON: 512 MiB, 300 s, 2.073.600 pixels/frame
  e 36.000 frames decodificados. Checar headers e durante decode; metadados
  são declarados, não prova de integridade do arquivo inteiro.
- Usar PTS×time_base em ordem de apresentação. Tempo zero é o primeiro frame
  do stream, preservando esse origin no metadata; recorte [start_s,end_s) não
  renumera frames/timestamps de origem. Rejeitar PTS ausente/não crescente
  por padrão. Fallback CFR só com FPS explicitamente fornecido pelo usuário,
  aplicado à sequência inteira e marcado `fps_fallback`; não inferir CFR de
  um FPS médio em vídeo VFR. Validar VFR com fixtures de PTS conhecidos.
- Exportação H.264/MP4, sem resize, dimensões pares para yuv420p; timeline
  exportada inicia no primeiro frame selecionado e preserva intervalos PTS.
  Duração do último frame usa duração fornecida pelo decoder ou FPS declarado
  como fallback documentado. Frames CSV preserva o mapeamento temporal.
- Fechar decoder/encoder/arquivos mesmo em erro/cancelamento. Diretório de saída
  deve ser novo; arquivos finais só são publicados após sucesso. Resultados
  incompletos mantêm marcação `.partial` e `failure.json`. Sem sobrescrita.
- Consequência: bounds, codecs, timestamp policy e ambiente acompanham cada
  execução; não há detecção, tracking, worker ou endpoints de upload nesta onda.
- Referências: [PyAV time](https://pyav.org/docs/stable/api/time.html),
  [exemplo oficial de PTS](https://github.com/PyAV-Org/PyAV/blob/main/examples/numpy/generate_video_with_pts.py).

## ADR-008 — Dados do piloto e separação de cenas

- Data: 2026-10-15. Estado: aceito para planejamento do piloto, sem dados baixados.
- Decisão: identificar SDD como fonte inicial com termos publicados CC BY-NC-SA 3.0
  para pesquisa não comercial; slots de cenas nexus/deathCircle/gates no inventário
  planejado. Validar caminhos e estabilidade de câmera ao obter os arquivos.
- Consequência: não prometer câmera fixa, cobertura de todas as classes, densidade
  ou oclusão antes da inspeção. Vídeos da mesma cena ficam no mesmo split.
  Congelar teste antes de ajuste quantitativo; frames aleatórios não são splits.
- Fixtures CFR/VFR são próprias e sintéticas, sem valor como benchmark real.
  GT de crossing começa na Onda 4; conversão/avaliação MOT na 7.
- Referência: [plano, termos publicados e gates](../datasets.md).

## ADR-009 — Detector baseline e dependências opcionais

- Data: 2026-10-15. Estado: aceito para implementação da Onda 2.
- Decisão: YOLO11n COCO da release oficial de assets v8.3.0, checkpoint com
  SHA-256 fixado no catálogo. Instalar Ultralytics headless 8.4.177 e PyTorch
  CPU via extra detector, sem substituir OpenCV headless por variante GUI.
- O catálogo publica disponibilidade de configuração, não presume arquivo
  baixado. Preparação é explícita; inferência exige checkpoint local e hash
  correto antes de carregar pesos. Nada de download implícito ou arquivo arbitrário.
- Preprocessamento letterbox quadrado explícito em BGR uint8, com metadados
  afins; YOLO devolve boxes na tela letterboxed e o adapter faz uma única
  inversão para coordenadas originais. Validar orig_shape do resultado SDK.
- Confidence de entrada 0.1 e visualização 0.25 como pontos de partida não
  otimizados. Exportar todas as detecções aceitas, não só as desenhadas.
  Parâmetros do ByteTrack ainda não existem; compatibilidade final é gate da Onda 3.
- CPU é o baseline empacotado. Código aceita CUDA somente se runtime disponível,
  com sincronização para medição; não alegar teste GPU em ambiente sem GPU.
- Medir preprocessamento, chamada de predict, normalização, inferência reportada
  pelo SDK e renderização separadamente, com warm-up fora das estatísticas.
- Fonte/licença: documentação e pesos Ultralytics sob AGPL-3.0 ou Enterprise;
  uso local de pesquisa não define LICENSE do monorepo nem autoriza redistribuição
  de exemplos de terceiros. Registrar termos e fontes no inventário técnico.
- Referências: [YOLO11](https://docs.ultralytics.com/models/yolo11/),
  [predict](https://docs.ultralytics.com/modes/predict/),
  [headless](https://docs.ultralytics.com/quickstart/),
  [licenças](https://www.ultralytics.com/license),
  [PyTorch CPU/uv](https://docs.astral.sh/uv/guides/integration/pytorch/).

## ADR-010 — ByteTrack concreto, estado temporal e trajetórias

- Data: 2026-10-15. Estado: aceito e implementado na Onda 3.
- Usar `ultralytics.trackers.byte_tracker.BYTETracker` da distribuição headless
  8.4.177, já fixada para YOLO; fixar também `lap==0.5.13`. Nenhuma cópia ou
  aproximação própria do algoritmo. Importação opcional pelo extra detector;
  testes reais marcados `tracker`, separados da suíte sem Torch.
- Adapter recebe detecções xyxy originais, converte para a interface NumPy do
  SDK e avança em todo frame, inclusive vazio. Não passar pelo filtro de desenho.
  Exigir detector.confidence <= track_low_thresh e low < high <= new.
- Buffer em chamadas/frames processados, stride=1, sem ajuste pelo FPS declarado.
  Exigir índices consecutivos e PTS crescentes; recortes podem começar em índice
  não zero. Kalman tem passo unitário, sem modelar dt variável de VFR. PTS reais
  continuam nos CSVs; buffer não representa tolerância em segundos.
- Expirar lost antes da associação quando `frame_atual - último_observado > buffer`.
  O upstream verifica idade após associação; o adapter restringe esse detalhe para
  impedir reviver IDs expirados. Recuperação no limite inclusivo é testada.
- Associação agnóstica à classe do upstream, classe congelada na primeira detecção
  do ID, inclusive fase não confirmada. Isso evita alternância de agregados; não
  corrige uma classificação inicial errada nem resolve ambiguidades de oclusão.
- IDs são locais à instância/execução, reiniciados em 1; não representam pessoas
  ou veículos persistentes. Testar instâncias intercaladas, reset e duas execuções.
- Observed usa a caixa/confiança da detecção associada; lost usa caixa estimada,
  confidence=null e não gera ponto de trajetória nem overlay. Novas entradas após
  o primeiro update exigem confirmação upstream; não retropreencher pontos.
- História recente: deque por ID, 64 pontos padrão, apenas IDs vivos/perdidos.
  Limite padrão 4.000 tracks vivas, erro explícito ao exceder. Pool removed do SDK
  limitado a 1.000. CSV completo em streaming, sem listas de todas as identidades.
- Preservar tracks curtas nos dados auditáveis; `min_observations=3` marca
  `analysis_eligible` no fechamento para filtragem de análise posterior. Não é
  remoção retroativa de CSV nem regra de crossing (Onda 4).
- Última observação encerra o span observado; término da seleção é censurado,
  não saída geométrica. Logs permitem investigar fragmentação; sem GT não
  computar ID switches, IDF1 ou HOTA. Ver [contratos operacionais](../tracking.md).
- Fontes primárias: [implementação fixada](https://github.com/ultralytics/ultralytics/blob/v8.4.177/ultralytics/trackers/byte_tracker.py),
  [gestão dos pools](https://github.com/ultralytics/ultralytics/blob/v8.4.177/ultralytics/trackers/utils/stracks.py),
  [artigo ByteTrack](https://arxiv.org/abs/2110.06864).
