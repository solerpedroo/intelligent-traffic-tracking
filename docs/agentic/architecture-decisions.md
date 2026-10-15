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
- Ondas 2–5: resolvidas por ADR-009 a ADR-012.
- Onda 6: resolvida por ADR-013.
- Onda 7: protocolo e conversores resolvidos por ADR-014. O baseline real
  continua bloqueado: splits não auditados, conforme ADR-008.
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

## ADR-011 — Crossing finito, confirmação e auditoria

- Data: 2026-10-15. Estado: aceito e implementado na Onda 4.
- LineConfig persiste endpoints normalizados no plano contínuo [0,width]×[0,height].
  Converter para pixels originais por execução; clipping somente no desenho.
  Máximo 16 linhas, IDs únicos, coordenadas finitas, endpoints distintos.
- Referência: centro inferior da caixa observada. Sinal de `(end-start)×(point-start)`:
  A negativo, B positivo. Inverter endpoints inverte sentidos. Lost/predicted não
  geram evidência. Fora da imagem quebra a sequência geométrica.
- Histerese padrão 3 px por distância perpendicular, borda da banda inclusiva.
  Estabelecer cada lado com duas observações fora da banda, sem interrupção pela
  banda/lado contrário. Preservar o lado estável anterior durante a passagem.
  Exigir três observações válidas da track no momento da confirmação.
- A evidência de interseção vem dos segmentos entre observações adjacentes
  aceitas, não da corda entre duas âncoras distantes. Assim, contornar endpoint
  pela banda não vira crossing. Endpoints são inclusivos, colinearidade excluída;
  um toque só conta se houver passagem e estabilidade no lado contrário.
- Controlar os sinais geométricos também dentro da banda; ida/volta dentro dela
  não pode deixar uma interseção antiga válida para uma passagem pela extensão.
- Lacunas: diferença máxima inclusiva de 1 frame e 0.5 s por padrão. Exigir ambos,
  inclusive em VFR. Comparação temporal admite 1 ns para arredondamento float.
  Lacuna excessiva perde âncora/estabilidade/interseção, mas mantém flags emitidas.
- Evento no frame/PTS de confirmação, sem estimar instante físico exato. Registrar
  âncora anterior, interseção em pixels e número de observações. Essas evidências,
  quando fornecidas, são completas e precedem a confirmação; contrato mínimo da
  Onda 0 continua legível sem campos opcionais.
- Deduplicar por run/linha/ID/sentido. Flags de ambos os sentidos vivem no estado
  da track; expulsá-las quando o adapter remove definitivamente o ID. Isso exige
  IDs nunca reutilizados na execução, garantidos pelo adapter ByteTrack. Novo ID
  pode duplicar um veículo físico; não usar isso como reidentificação.
- CSV de eventos incremental, summary por linha/classe/sentido. Janelas esparsas
  de mídia `[k*window_s,(k+1)*window_s)` em CSV, ancoradas no zero original e
  classificadas pelo PTS de confirmação. Aritmética decimal das representações
  evita classificar 0.3 s em [0.2,0.3) por arredondamento binário. Somente a janela
  atual fica em RAM; zeros implícitos no CSV, totais de linha/sentido explícitos.
- Validação real inicial com exemplo público vehicles.mp4 do Supervision,
  derivação e anotações visuais de desenvolvimento documentadas. Não declarar
  GT independente, teste congelado ou benchmark de acurácia. Ver [dados](../datasets.md)
  e [contrato operacional](../counting.md). Sem dependências novas.

## ADR-012 — ROI observada, censura de visitas e heatmaps limitados

- Data: 2026-10-15. Estado: aceito e implementado na Onda 5.
- ZoneConfig persiste polígonos simples normalizados com 3–64 vértices, até 16
  zonas. Rejeitar repetição de vértice inicial, área quase nula, cruzamentos,
  auto-toques e arestas que retrocedem. Aceitar concavidade, orientação inversa e
  vértices colineares sem retrocesso. Sem buracos. Borda/vértices são interiores.
- Usar centro inferior da detecção associada, como nas linhas. Ocupação é número
  de IDs observados por frame/zona/classe, não quantidade física de veículos.
  Zonas sobrepostas contam independentemente. CSV inclui zeros e PTS originais.
- Abrir visita por transição observada de fora para dentro. Primeira observação
  já dentro é censurada à esquerda, sem inventar entrada: selection_start,
  first_observation_inside ou after_observation_loss. Um ID pode ter várias visitas.
- Dwell aproximado soma somente dt entre frames consecutivos com ponto dentro
  da mesma ROI e dt<=max_gap_s (padrão 0.5 s, tolerância de arredondamento 1 ns).
  Não somar intervalos outside→inside/inside→outside, duração de exposição do
  último frame, tempo até o fim do recorte ou períodos sem observação.
- Lost/predicted, remoção do ID, ponto fora da imagem e lacuna temporal excessiva
  encerram visitas como observation_lost com censura à direita; evento informa
  motivo específico. Recuperação abre novo trecho censurado. Saída geométrica
  exige observação válida fora da ROI; fim da seleção é selection_end censurado.
- Reset por execução; estado apenas para IDs vivos/perdidos, limitado pelo mesmo
  max_live_tracks do tracker. Visitas encerradas/eventos/ocupação são persistidos
  incrementalmente, sem manter histórico completo de visitas em RAM.
- Heatmap global da imagem, independente das ROIs: uma contribuição por ID
  observado/frame, inclusive baixa confiança. Classe estabilizada pelo tracker;
  filtro explícito de classes ou classes do detector. Máximo 16 classes e grade
  256×256 uint64, só uma janela em RAM (até 8 MiB de grades brutas).
- Janelas de mídia [k*window_s,(k+1)*window_s), origem original, aritmética decimal.
  Exportar somente janelas com frames processados; classes sem observações nessa
  janela têm grade zero. Saltos sem frames não geram informação presumida.
- NPZ guarda raw e smoothed; suavização gaussiana em células, sigma padrão 1,
  raio ceil(3*sigma), zero padding com renormalização global para conservar massa.
  Sigma zero desativa. PNG Inferno normalizado pelo pico de cada mapa, zero preto;
  cores entre arquivos não representam a mesma quantidade absoluta.
- Unidade: observações/célula. Sem peso por dt ou normalização por área física;
  FPS, duração da janela e permanência influenciam o resultado. Não chamar isso
  de passagens únicas, densidade física, velocidade ou congestionamento.
- Preview com falha mantém NPZ numérico em heatmaps.partial e sinaliza erro.
  Integridade/publicação numérica independente da renderização será consolidada
  na Onda 6. Contratos operacionais: [zones-heatmaps.md](../zones-heatmaps.md).

## ADR-013 — Exports versionados e falha de renderização (Onda 6)

- Data: 2026-10-15. Estado: aceito para implementação.
- Decisão: schema de exportação `1.0` em `vision/pipeline/schemas.py`, com colunas
  e unidades. Toda execução bem-sucedida no núcleo publica `config.json`,
  `manifest.json`, `summary.json` e os CSV aplicáveis. `config.json` guarda a
  configuração resolvida e pode ser recarregada por JSON.
- `render_annotated_video=false` ou `--no-annotated-video` não gera MP4. O
  summary fica `completed_with_warnings`, com `annotated_video_skipped`. CSV,
  NPZ, manifest e summary continuam válidos (`numeric_results_valid`).
- Falha de overlay, encoder, finalização do MP4 ou preview PNG não falha o
  núcleo. O vídeo ou o preview não é promovido; o summary registra `failed` ou
  o aviso correspondente. Falha de decode, detector, tracker, contagem, analytics
  ou escrita de tabela continua `failed`/`cancelled`, com `failure.json` e sem
  summary de sucesso.
- Preview de heatmap que não codifica PNG conserva o NPZ e deixa `preview_file`
  vazio, com aviso. Publicação final continua atômica: `.partial` só é renomeado
  depois do fechamento. Um encoder que apaga um MP4 vazio não cria um vídeo
  publicado.
- Consequência: ausência de vídeo anotado não é execução incompleta do núcleo.
  MOT segue `not_evaluated_no_ground_truth` sem GT. Avaliação real permanece
  na Onda 7.

## ADR-014 — Protocolo de avaliação e TrackEval (Onda 7)

- Data: 2026-10-15. Estado: aceito para implementação; baseline real bloqueado.
- Decisão: congelar IoU 0,50:0,95, AP de 101 pontos, tolerância de evento de
  0,5 s e IoU de associação 0,5 em `experiments/configs/evaluation-protocol.json`
  antes de medir sequências externas. O registro de splits permanece
  descongelado até haver hash e auditoria.
- Detecção, contagem e desempenho são calculados no núcleo. MOT só chama
  TrackEval 1.3.0, por classe, gravando essa classe como id 1 do MOTChallenge
  e com `DO_PREPROC` desligado. Sem `track_id` na referência, o resultado é
  `not_evaluated`, nunca HOTA zero.
- A dependência publicada do TrackEval pede `opencv-python` 5, que substitui o
  `cv2` headless 4.14 do extra `video`. O metadado resolvido pelo uv fica
  restrito a NumPy, SciPy e tabulate. O extra `evaluation` declara de novo o
  OpenCV headless já usado pelo vídeo.
- Consequência: a CLI recusa `frozen_test_benchmark` enquanto o teste não
  estiver congelado. Fixtures sintéticas validam indexação e erros conhecidos,
  mas não fecham o gate científico. A Onda 8 espera esse baseline.
