# Intelligent Traffic Tracking — Plano de implementação

Versão: 1.0 · Data: 2026-10-15 · Estado: ondas 0–2 implementadas e validadas localmente; ondas 3–12 planejadas.
Fonte de requisitos: [project-scope.md](project-scope.md).
Interpretação e adaptações: [scope-analysis.md](scope-analysis.md).

## 1. Objetivo e estratégia

Entregar um pipeline científico de detecção, tracking e contagem em vídeos de
câmera fixa, seguido por uma aplicação web que permita executar e auditar os
mesmos algoritmos. Documentação em português; código, API, CLI e UI em inglês.

Adota-se a ordem da seção 20 do escopo: núcleo Python → avaliação → aplicação
web. As ondas detalham as sprints da seção 11 sem atribuir duração artificial.
Este plano e os cartões são especificações; comandos e evidências de execução
serão registrados quando houver implementação.

## 2. Pilares e marcos

- **Núcleo desacoplado:** vídeo, detecção, tracking, geometria e analytics em
  `vision/`, sem dependência de FastAPI ou React.
- **Correção temporal e geométrica:** sequência, timestamps, identidade local,
  linhas finitas, histerese, ocupação e limites de memória explícitos.
- **Ciência verificável:** dados de referência, splits por sequência,
  métricas válidas, resultados reais e análise de falhas.
- **Reprodução:** CLI, configurações versionadas, manifest e hashes.
- **Confiabilidade operacional:** jobs, persistência, recuperação, cancelamento
  e artefatos íntegros.
- **Experiência completa:** configurar → executar → inspecionar → comparar → exportar.
- **Engenharia contínua:** tarefas limitadas, contratos, revisão e contexto durável.

Marcos:

1. Onda 1: leitura e exportação de vídeo via CLI.
2. Onda 6: núcleo funcional completo e exports auditáveis.
3. Onda 8: baseline avaliado e experimentos A/B/C documentados.
4. Onda 11: fluxo completo pelo navegador.
5. Onda 12: aceitação final e portfólio reproduzível.

## 3. Modelo de entrega

Sequência: **0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12**.
Cada onda termina ao cumprir seus critérios de pronto e registrar evidências.
Pode haver tarefas menores dentro de uma onda; a próxima exige o fechamento
da anterior ou uma alteração documentada de dependências.

Cada tarefa declara requisitos, arquivos permitidos, contratos, testes e
exclusões. Cursor e Codex usam [AGENTS.md](../AGENTS.md), os mesmos cartões e
o [workboard](agentic/workboard.md). A posse de arquivos compartilhados deve ser
serializada caso o usuário utilize sessões simultâneas.

O agrupamento do escopo permanece reconhecível: sprint 1 → ondas 0–1;
sprint 2 → onda 2; sprint 3 → onda 3; sprint 4 → ondas 4–5 e editor na 10;
sprint 5 → ondas 9–11; sprint 6 → ondas 7–8, antecipadas conforme seção 20;
sprint 7 → onda 12. Testes e documentação acompanham todas as ondas.

## 4. Estrutura alvo do monorepo

```text
intelligent-traffic-tracking/
├── AGENTS.md
├── README.md
├── pyproject.toml                 # pacote vision e ferramentas Python
├── frontend/                      # Next.js, TypeScript, UI e cliente tipado
│   ├── app/                       # workspace, jobs, viewer, analytics, experiments
│   ├── components/
│   ├── features/
│   ├── lib/
│   └── types/
├── backend/
│   ├── app/                       # api, schemas, services, storage, jobs, core
│   └── tests/
├── vision/
│   ├── contracts/                 # dados internos, sem modelos HTTP
│   ├── video/                     # decode, probe, timestamps
│   ├── detectors/
│   ├── trackers/
│   ├── pipeline/                  # orquestração e CLI
│   ├── geometry/
│   ├── counting/
│   ├── analytics/
│   ├── rendering/
│   ├── evaluation/
│   ├── datasets/                  # adaptadores; não vídeos baixados
│   ├── configs/                   # catálogo e presets versionados
│   └── tests/
├── experiments/                   # configs, notebooks opcionais, reports
├── examples/                      # fixtures autorizadas e pequenos resultados
├── scripts/                       # preparação dos dados e utilitários
├── docs/                          # arquitetura, API, dados, avaliação, metodologia
│   └── agentic/                   # decisões, tarefas, workboard e handoffs
├── .cursor/rules/
├── .github/workflows/
└── .gitignore
```

Essa é a estrutura alvo; pastas de código serão criadas nas ondas responsáveis.
Dados grandes, checkpoints e runtime storage ficam fora do Git. `vision/datasets/`
contém código; a raiz de dados é configurável e externa ao pacote.

## 5. Contratos e invariantes técnicos

### 5.1 Fronteiras

`vision/` implementa algoritmos e pipeline reutilizáveis. Adapters de vídeo e
renderização podem acessar arquivos; contadores e geometria não acessam HTTP,
banco ou ambiente global. Dependências/configurações são injetadas.
`backend/` traduz HTTP, persiste jobs e chama o pipeline por um worker separado.
`frontend/` apresenta resultados; não reimplementa inferência ou contagem.
CLI e worker usam o mesmo pipeline, sem bifurcar as regras científicas.

### 5.2 Dados internos

Na Onda 0, definir e testar contratos para `FramePacket`, `Detection`, `Track`,
`TrackObservation`, `CrossingEvent`, `ZoneEvent`, `ProcessingConfig`,
`RunManifest` e progresso. Evitar carregar dependências de modelos no health check.

- Frames: array BGR `uint8` H×W×3 no decode OpenCV; conversão RGB apenas na
  fronteira que exigir. Registrar convenção do adaptador do detector.
- Boxes: `xyxy` em pixels da imagem original, origem superior esquerda;
  transformações de resize/letterbox devem ser reversíveis e testadas.
- Geometria persistida: coordenadas normalizadas em `[0,1]`, sem segmentos
  degenerados ou polígonos inválidos; histerese em pixels originais no baseline.
- Índice de frame: zero-based do vídeo original; timestamps em segundos da
  mídia original, mesmo com seleção de trecho. Não confundir tempo da mídia
  com duração de execução ou posição no vídeo exportado.
- IDs: locais à execução. Chaves externas incluem `job_id`/`run_id` e `video_id`;
  usar `run_id` como identidade também na CLI e mapear para `job_id` no backend.
- Observações: distinguir medição atual, predição e track perdido. Contagem e
  ocupação no baseline usam observações atuais elegíveis.
- Classe da track: política de estabilização e comportamento diante de mudança
  de classe definidos na Onda 3; nunca somar uma track em classes incompatíveis.

### 5.3 Tempo e estado

Frames são consumidos na ordem. Preferir PTS reais para VFR; se a fonte não os
fornecer de modo confiável, rejeitar esse modo ou aplicar fallback explicitamente
marcado, conforme ADR da Onda 1. `frame_index / fps` não é verdade universal.

Baseline com `frame_stride=1`. Antes de habilitar stride maior, testar a unidade
do `track_buffer`, a cadência entregue ao tracker, o tempo de permanência e a
relação entre timeline original e renderizada. Não inventar observações perdidas.
Resetar tracker, contador e ROI por execução. Buffers em RAM são limitados;
trajetórias completas são gravadas incrementalmente.

### 5.4 Detecção e tracking

Catálogo em `vision/configs/` define modelos permitidos, class mapping,
presets e limites de parâmetros; API e UI consomem o contrato, sem defaults
divergentes. Checkpoint, versão e hash constam do manifest.

Selecionar uma implementação concreta de ByteTrack e fixar dependências na
Onda 2–3. Garantir compatibilidade entre threshold de saída do detector e a
associação de baixa confiança do ByteTrack. Filtros da visualização não podem
eliminar as detecções que o tracker precisa. Testar integração de verdade;
um mock do tracker não demonstra continuidade de ID.

### 5.5 Crossing e ROI

Para linha orientada `start → end`, usar o sinal do produto vetorial
`(end-start) × (point-start)`: lado A negativo, lado B positivo; `A_TO_B`
significa negativo → positivo. A banda usa distância perpendicular em pixels.
A interface explica essa convenção e inverter endpoints inverte os lados.

Exigir evidência estável de ambos os lados fora da banda, comprimento mínimo
de track e interseção do movimento com o segmento finito. Preservar a última
observação estável durante passagem pela banda. Definir limite de lacuna temporal
para impedir uma travessia inferida entre observações muito distantes.

Deduplicar por `(run_id, line_id, track_id, direction)`. Dois sentidos são
independentes; nova travessia na mesma direção não rearma no MVP. Novo ID após
oclusão continua sendo uma fonte de erro a medir.

ROI inclui pontos sobre a borda. Baseline mede presença de tracks observadas,
registra perda como motivo distinto de saída geométrica e não prolonga dwell
por lacunas desconhecidas. Intervalos de permanência são aproximados e devem
explicitar censura no começo/fim do vídeo e política temporal.

### 5.6 Jobs e artefatos

Estados base: `queued → running → completed | failed | cancelled`.
Cancelamento de `queued` é permitido; de `running`, uma solicitação persistida
é atendida no próximo ponto seguro. `completed` admite aviso de vídeo ausente
somente se os resultados numéricos obrigatórios forem íntegros e o manifest
de artefatos marcar o erro; falha do núcleo é `failed`, com parciais identificados.

MVP com um worker e um job ativo por vez. Claim do job é transacional no SQLite;
progresso/heartbeat e política de recuperação após crash são obrigatórios.
Na primeira versão, execução interrompida vira `failed` com motivo recuperável;
reprocessar cria novo job, sem retomar estado temporal parcialmente reconstruído.
Não prometer execução exatamente uma vez após crash.

Publicar artefatos finais por escrita temporária e rename; preservar parciais
identificados. Downloads usam catálogo permitido e caminhos internos resolvidos,
nunca um caminho arbitrário informado pelo cliente. Não remover arquivos de
jobs ativos durante limpeza. Definir retenção, cotas e logs sem frames/payloads.

### 5.7 Reprodutibilidade e avaliação

Manifest versionado com hash de entrada, trecho, pesos/hash, parâmetros
resolvidos, geometria, política temporal, mapeamento de classes, seeds,
hardware, dependências, commit e indicador de árvore Git modificada.
Registrar manifest inicial e completar ao término, inclusive em falhas.

Dados: 2–3 vídeos fixos autorizados para demonstração/contagem, mais sequências
com boxes e IDs para MOT quando necessário. Diferenciar conjuntos de demonstração,
ajuste e teste. Disponibilidade/licença e viabilidade das anotações são um gate
desde a Onda 1; não pressupor que os mesmos vídeos oferecem todos os rótulos.

- Detecção: Precision/Recall e mAP@50:95, com boxes e protocolo adequado.
- MOT: TrackEval, conversor testado, HOTA/IDF1/MOTA/ID switches com GT de IDs.
- Contagem: erro por vídeo/linha/classe/sentido; erro relativo com GT zero é
  `null` acompanhado do erro absoluto, não divisão por zero.
- Eventos: pareamento um a um na mesma linha/classe/sentido, tolerância temporal
  fixada antes da avaliação; reportar TP/FP/FN e convenção de denominador zero.
- Computação: decode/inferência/tracking/analytics/render/I/O separados;
  warm-up explicitado, sincronização CUDA quando necessária, média/mediana/p95,
  RAM/VRAM quando disponíveis, throughput end-to-end e tamanho dos artefatos.

Não estabelecer metas de HOTA/IDF1/FPS antes do baseline. Ausência de referência
é `not_evaluated` com motivo, nunca zero ou resultado estimado. O gate científico
final exige referências válidas; demonstração qualitativa não o substitui.

## 6. Ondas de implementação

### Onda 0 — Fundação executável e contratos

Requisitos: escopo §§3–4, 9, 12–13. Depende da documentação inicial.

Entregar pacote Python instalável, shell Next.js, FastAPI health, configuração
de ambiente, contratos internos e catálogo inicial sem modelos carregados.
Fixar ferramentas/lockfiles e comandos de instalação, lint, testes e build.
CI leve sem GPU, downloads de pesos ou vídeos de terceiros. Documentar
arquitetura e API inicial. Não implementar upload ou inferência nesta onda.

Testes: contratos válidos/inválidos, health e shell; importação do núcleo sem
FastAPI. **Pronto:** instalação limpa, checks locais e CI passando, contratos
versionados, comandos reais registrados no cartão.

### Onda 1 — Vídeo, timestamps, CLI e plano de dados

Requisitos: M01, §§6, 11/sprint 1, 17. Depende de 0.

Entregar probe, decode sequencial, preview, trecho temporal, CLI mínima e
exportação de vídeo sem inferência. Validar conteúdo/codec, dimensões, duração
e limites configuráveis; documentar capacidades locais de FFmpeg e política
VFR. Selecionar fontes, registrar licenças/proveniência, splits e plano de GT
em `docs/datasets.md`. Criar fixtures pequenas sintéticas/autorizadas.

Testes: CFR/VFR quando suportado, timestamps, vídeo vazio/corrompido,
interrupção e fechamento de recursos. **Pronto:** vídeo round-trip reproduzível,
limites explícitos, tempo consistente e dados/anotações viáveis identificados.

### Onda 2 — Detector YOLO e baseline de inferência

Requisitos: M02, §§3, 17. Depende de 1.

Entregar `DetectorAdapter`, checkpoint leve fixado, class mapping real,
thresholds, inversão de letterbox/resize e vídeo de detecções. Configurar CPU
e GPU opcional; registrar manifest inicial e timings. Verificar documentação
oficial e termos efetivos dos componentes ao escolher versões/pesos.

Testes: mapeamento de classes, boxes em diferentes proporções, saída vazia,
parâmetros inválidos e smoke real do detector. **Pronto:** CLI produz detecções
nas coordenadas originais, tempos separados e execução CPU comprovada. Smoke
com pesos é explícito e separado da CI leve; não marcar como executado se pulado.

### Onda 3 — ByteTrack e trajetórias

Requisitos: M03 e parte de M06. Depende de 2.

Entregar `TrackerAdapter`, integração real, estado por execução, frames sem
detecções, tracks perdidas, classe estabilizada, história recente limitada e
trajetórias completas em streaming. Renderizar IDs e rastros. Registrar todos
os parâmetros, incluindo unidade do buffer e a política de amostragem.

Testes: sequências controladas com a implementação real, entrada/saída,
oclusão curta, buffer, reset entre vídeos e passagem de detecções fracas.
**Pronto:** IDs mantidos quando esperado nos cenários controlados, reset
comprovado e memória independente da duração para os buffers recentes.
Sem GT, fragmentação suspeita não é rotulada como ID switch confirmado.

### Onda 4 — Linhas, direção e contagem auditável

Requisitos: M04, §§12.1, 14. Depende de 3.

Entregar geometria finita, centro inferior, lados A/B, histerese, elegibilidade,
deduplicação, eventos e agregação por classe/sentido. Geometrias vêm da
configuração CLI nesta fase. Criar pequenas anotações manuais de crossing para
validar o fluxo real antes do benchmark completo.

Testes: horizontais/verticais/diagonais, ambos os sentidos, toque sem travessia,
trajeto pela banda, jitter, extensão fora dos endpoints, lacuna excessiva,
track curta/desaparecida, fora da imagem, múltiplas linhas/classes, retorno e
reset. **Pronto:** contagens sintéticas exatas, cada incremento rastreável a um
evento e comparação manual documentada, incluindo divergências observadas.

### Onda 5 — ROI, permanência e heatmaps

Requisitos: M05–M06. Depende de 4.

Entregar polígonos, entradas/saídas, ocupação por timestamp, dwell aproximado,
export de trajetórias e heatmaps por classe/janela. Documentar borda, perda,
censura e peso temporal das observações. Presença na imagem não é densidade
física ou congestionamento; heatmap de observações não é passagem única.

Testes: bordas/vértices, polígonos inválidos, zonas sobrepostas, entrada/saída,
perda de observação, início/fim dentro da ROI e tempos irregulares.
**Pronto:** séries e permanência verificáveis em trajetórias sintéticas;
heatmap com unidades, acumulação e suavização registradas.

### Onda 6 — Exports, renderização e integridade do núcleo

Requisitos: M07, M10 e P0. Depende de 5.

Consolidar `crossing_events.csv`, `tracks.csv`, eventos/séries de zona,
`summary.json`, `config.json`, `manifest.json`, heatmaps e vídeo anotado.
Versionar schemas, definir unidades e preservar configuração resolvida.
Renderizar linhas, zonas, IDs, rastros e contadores; documentar timeline e
codec do output. Tratar falhas de render sem perder eventos calculados.

Testes: pipeline curto completo, reconciliação summary↔eventos, schemas,
export vazio válido, escrita interrompida, falha de codec e repetição de config.
**Pronto:** CLI reproduz o núcleo completo com artefatos íntegros e execução
sem vídeo anotado preserva resultados numéricos, com aviso explícito.

### Onda 7 — Avaliação e benchmark científico

Requisitos: M09, §§6, 10.1, 12.4. Depende de 6.

Entregar adaptadores de anotações, conversão para TrackEval, avaliação de
detecção, MOT, contagem/eventos e desempenho. Congelar splits, tolerâncias e
protocolo antes de ajustar parâmetros. Registrar hashes de GT e resultados
por sequência e agregados em `docs/evaluation.md` e `docs/methodology.md`.

Testes: GT/predição perfeitos e erros conhecidos; convenção de frames/IDs,
classes ignoradas, fronteiras temporais, GT zero e denominadores vazios;
conversor sem off-by-one. **Pronto:** baseline real com referência adequada,
scripts CLI e resultados reproduzíveis; limitações e cobertura das anotações
claras. Não exigir métrica MOT de vídeo que só tem anotação de contagem.

### Onda 8 — Experimentos A/B/C e análise de falhas

Requisitos: M10, §§10, 14, 16. Depende de 7.

Entregar estudos mínimos de parâmetros ByteTrack (A), densidade/oclusão (B) e
degradações controladas (C), todos via CLI. Fixar hipóteses, fatores, controles,
sequências, hardware e seeds. Definir estratos B antes de olhar resultados;
manter alinhamento temporal/GT nas transformações C e documentar intensidades.

Cada relatório inclui configs, comando, manifests, resultados reais por
sequência, figuras, falhas e limitações. Repetir condições aleatórias conforme
protocolo; não alegar significância com poucas sequências.
**Pronto:** três estudos executados e reproduzíveis. Arquivos de protocolo
vazios ou números sintéticos não fecham esta onda. Fine-tuning, BoT-SORT e
robustez ampliada continuam como extensões.

### Onda 9 — API, worker, SQLite e ciclo de jobs

Requisitos: §7, M10, parte do M01 web. Depende de 8.

Entregar upload persistido, preview, catálogo e rotas do escopo §7.1:
`GET /api/health`, `POST /api/videos`, `GET /api/videos/{video_id}`,
`GET /api/models`, `POST /api/jobs`, `GET /api/jobs`,
`GET /api/jobs/{job_id}`, `POST /api/jobs/{job_id}/cancel`,
`GET /api/jobs/{job_id}/summary`, `/events`, `/tracks`,
`/artifacts/{name}` e `GET /api/experiments`.

Criação retorna 202. Worker separado da API; claim atômico, progresso,
heartbeat, recuperação de crash, cancelamento, paginação, downloads permitidos,
retenção/cotas e migrações. Testar parciais e erros de disco. Documentar códigos,
schemas e transições em `docs/api-contract.md`.

Testes: upload inválido, concorrência de claim, API reiniciada sem matar worker,
worker interrompido/reiniciado, cancelamento queued/running, reprocessamento
isolado, path traversal e limpeza sem afetar job ativo.
**Pronto:** ciclo completo via HTTP sem requisição longa e sem executar
inferência dentro do processo servidor; parciais e falhas não aparecem como sucesso.

### Onda 10 — Workspace web, editor e viewer

Requisitos: §8, M01/M04/M05/M07 web. Depende de 9.

Entregar Overview, Video Workspace, Processing Jobs e Tracking Viewer:
upload, preview, seleção de trecho/classes/modelo, linhas/zonas editáveis,
parâmetros do catálogo, polling/progresso, cancelamento, erros, vídeo e downloads.
Coordenadas do editor devem considerar redimensionamento, aspect ratio e
letterboxing da exibição. UI em inglês, dark mode e azul, desktop/tablet;
controles acessíveis e alternativa por campos às ações de desenho.

Testes: transformações do editor, parâmetros inválidos, polling encerrado em
estado terminal, erro recuperável e E2E upload→linha→job→resultado→download.
**Pronto:** usuário conclui o fluxo sem editar Python; vídeo e contagens
correspondem ao job escolhido. Fixtures leves suportam CI; smoke real local
completa a evidência de integração com o núcleo.

### Onda 11 — Analytics, comparação e metodologia na interface

Requisitos: M08, §8.2. Depende de 10.

Entregar Traffic Analytics, Experiment Comparison e Methodology/About:
contagens por classe/sentido, séries com granularidade coerente, ocupação,
duração das tracks, heatmaps, latências e comparação entre execuções.
Galeria mostra fragmentação confirmada quando houver GT, ou suspeitas rotuladas.
Comparações indicam diferenças de vídeo, trecho, geometria, pesos e hardware;
não tratam execuções incompatíveis como ablação controlada.

Testes: agregados reconciliados com exports, vídeo curto, ausência de dados/GT,
métrica indisponível e comparação de jobs incompatíveis.
**Pronto:** números visíveis são rastreáveis aos artefatos; unidades, limitações
e motivo de métricas ausentes estão explícitos, inclusive em sequências vazias.

### Onda 12 — Aceitação, confiabilidade e portfólio

Requisitos: §§12–15, 17. Depende de 11.

Executar regressão, E2E real, instalação limpa e ensaio de execução longa com
memória/disco observados. Revisar permissões de dados, modelos e dependências
antes de selecionar LICENSE/publicar. README técnico em inglês com instalação,
dados, CPU/GPU, CLI, web, exemplos e limitações. Documentar arquitetura,
operação local, screenshots autorizados e produzir demonstração em vídeo.

Criar `docs/mvp-acceptance.md` com evidência para cada critério do escopo §14.
Deploy em nuvem é opcional e exige desenho de armazenamento persistente e
worker, validação de recursos e termos reais; não herdar Vercel/Railway como
decisão deste projeto.
**Pronto:** todos os critérios do MVP comprovados, três estudos reais, CI verde,
reprodução a partir de clone limpo e materiais de demonstração existentes.
Storyboard isolado não equivale ao vídeo final solicitado no escopo.

## 7. Rastreabilidade da aceitação do escopo §14

1. Importar vídeo/metadados: ondas 1, 9 e 10.
2. Detectar classes com YOLO: onda 2; uso web na 10.
3. IDs/trajectórias com estado: onda 3.
4. Desenhar linhas e definir sentidos: ondas 4 e 10.
5. Contar por classe/sentido: onda 4.
6. Evitar duplicação por jitter nos testes: onda 4.
7. ROI e ocupação por tracks: ondas 5 e 11.
8. Vídeo e eventos CSV/JSON: ondas 6, 9 e 10.
9. Dashboard de contagens/séries/desempenho: onda 11.
10. Jobs assíncronos com erros visíveis: ondas 9 e 10.
11. Testes críticos: desde 0; regressão final na 12.
12. Métricas MOT apenas com GT adequado: ondas 7 e 11.
13. Três experimentos reais: onda 8.
14. README de instalação/dados/limitações: instruções incrementais; final na 12.

O M10 acompanha 2–12; manifest completo e exports são gate da 6. O M09 fica
na 7; M01–M08 se distribuem entre núcleo e UI conforme descrito nas ondas.

## 8. Qualidade e critérios comuns de pronto

- Tarefa limitada à onda e aos arquivos declarados, sem novas features implícitas.
- Contratos, unidades, política de erros e limitações atualizados.
- Testes proporcionais: unitários determinísticos para contagem/geometria,
  integração real para modelos/pipeline e E2E para o fluxo de usuário.
- Fixtures sintéticas pequenas na CI; dados e pesos externos por preparação
  explícita. Marcar execução pulada e motivo; mock não comprova integração real.
- Python: Ruff e pytest; frontend: lint, typecheck, Vitest e build; Playwright
  quando o fluxo web existir. Fixar scripts e versões na Onda 0 e ampliar a CI
  quando cada camada entrar, sem criar checks vazios que aparentem cobertura.
- Evidências com comandos exatos e resultados no cartão; workboard atualizado.
- Revisão do diff, dos testes e da validade científica antes de fechar a onda.

## 9. Riscos, decisões pendentes e contenção

- **Dados/GT insuficientes:** validar fontes na 1 e anotar crossing na 4;
  não fechar avaliação ou MVP apenas com demos.
- **Quebra de integração YOLO/ByteTrack:** interfaces e versões fixadas,
  thresholds coerentes e smoke real nas ondas 2–3.
- **CPU/GPU/memória:** iniciar leve, um job ativo, buffers limitados, medir no
  hardware disponível. Hardware citado no escopo é referência, não benchmark.
- **Tempo/codec:** testar cedo, registrar fallback e timeline exportada.
- **Crash/duplicação/parciais:** claim transacional, heartbeat, execução isolada,
  persistência incremental e artefatos finais publicados atomicamente.
- **Licenças e distribuição:** inventário dos componentes/dados reais; decisão
  de LICENSE depende da verificação de termos, sem supor compatibilidade.
- **Drift Cursor/Codex:** AGENTS e cartões canônicos, regras Cursor curtas e
  sem decisões conflitantes, handoff factual para interrupções.

Permanecem a decidir nas ondas responsáveis: versões/checkpoint/ByteTrack,
ferramenta de timestamps, limites concretos de upload/retenção, codecs,
datasets/GT e eventuais provedores de hospedagem. Registrar ADR ao resolver.

## 10. Estado atual e próximo passo

Ondas 0–2 implementadas: fundação, CLI de vídeo, PTS/VFR, export e YOLO11n
com checkpoint verificado, boxes originais, manifest e timings. Evidências nos
cartões [0](agentic/tasks/wave-0-foundation.md), [1](agentic/tasks/wave-1-video-cli.md)
e [2](agentic/tasks/wave-2-detection.md). CI remota não foi verificada; datasets
reais ainda precisam de aquisição/auditoria. Próxima: [Onda 3](agentic/tasks/wave-3-tracking.md).
Não carregar modelos nem antecipar features de outras ondas ao retomar o trabalho.
