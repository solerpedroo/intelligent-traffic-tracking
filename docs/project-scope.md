Intelligent Traffic Tracking & Urban Mobility Analytics
Project Scope / Implementation Plan — Version 1.0
Projeto 03 — Portfólio de Visão Computacional / Preparação para Iniciação Científica
Idioma da documentação: Português; nomenclatura de código, API e interface em inglês.
Repositório sugerido: intelligent-traffic-tracking

1. Visão geral
O Intelligent Traffic Tracking será uma plataforma de análise de vídeos de trânsito baseada em detecção de objetos, rastreamento de múltiplos objetos (Multi-Object Tracking — MOT) e análise espaço-temporal. O sistema identificará veículos e pedestres, manterá IDs ao longo dos frames e produzirá contagens e métricas de circulação em regiões e linhas virtuais definidas pelo usuário.
O projeto deve ir além de uma demonstração de bounding boxes: precisa ter pipeline reprodutível, algoritmo de contagem testado, ferramentas de avaliação, métricas de tracking e visualizações de resultados. O aplicativo web será uma interface de demonstração e análise; o núcleo científico ficará em módulos Python independentes.
1.1 Objetivo geral
Desenvolver e avaliar um sistema capaz de detectar, rastrear e contar veículos e pedestres em vídeos de tráfego, gerando análises por classe, direção, período e região, com atenção especial à continuidade dos IDs, oclusões e desempenho computacional.
1.2 Objetivos específicos
1. Implementar um pipeline de leitura e processamento temporal de vídeos.
2. Integrar um detector YOLO e um rastreador ByteTrack por interfaces desacopladas.
3. Preservar identificadores temporários por objeto durante uma sequência.
4. Registrar trajetórias, direção de deslocamento e eventos de cruzamento.
5. Implementar line crossing com contagem por classe e direção, sem contagens duplicadas.
6. Implementar regions of interest (ROI) e estatísticas básicas de ocupação.
7. Produzir vídeos anotados, CSV/JSON de eventos e um dashboard analítico.
8. Medir detecção, tracking, contagem e desempenho de inferência separadamente.
9. Investigar sistematicamente falhas causadas por oclusão, densidade de tráfego, baixa iluminação e parâmetros do tracker.
10. Documentar hipóteses, protocolos experimentais, resultados e limitações para possível evolução em IC.
1.3 Perguntas que o sistema deverá responder
- Quantos carros, ônibus, caminhões, motos e pedestres cruzaram uma linha virtual?
- Em qual sentido ocorreu cada cruzamento?
- Quantos objetos de cada classe aparecem ou permanecem em determinada região?
- Quais trajetórias foram estimadas durante o vídeo?
- Em quais trechos ocorreram maiores concentrações de objetos detectados?
- Com que frequência os IDs foram perdidos ou trocados?
- Como diferentes configurações do detector e do rastreador afetam a precisão da contagem?
- Qual é o custo computacional de cada configuração?
2. Delimitação e decisões iniciais
2.1 Escopo do MVP
A primeira versão será projetada para vídeos previamente gravados por uma câmera predominantemente fixa. Essa restrição simplifica a definição de linhas e zonas e torna válidas as análises de fluxo por posição na imagem.
O MVP deverá suportar:
- Um vídeo por execução (.mp4, inicialmente; outros formatos mediante validação).
- Uma câmera por vídeo, sem associação de IDs entre câmeras.
- Inferência com detector YOLO pré-treinado, com classes configuráveis.
- Rastreamento com ByteTrack.
- Bounding boxes, classes, confidence scores e IDs na visualização.
- Uma ou mais linhas virtuais com contagem por classe e direção.
- Até algumas regiões poligonais configuradas pelo usuário, sujeitas a limites de interface.
- Históricos de trajetória e eventos de cruzamento.
- Exportação de vídeo processado, resultados e configuração.
- Dashboard com estatísticas agregadas e resultados de avaliação.
- Processamento assíncrono por job no backend, evitando requisições HTTP longas.
2.2 Fora do MVP
- Estimativa de velocidade em km/h sem calibração métrica confiável.
- Reconhecimento facial, identificação nominal de pedestres ou leitura de placas.
- Integração com câmeras urbanas reais e infraestrutura municipal.
- Rastreamento cruzado entre múltiplas câmeras e reidentificação persistente.
- Detecção automática de infrações de trânsito.
- Operação com drones/câmeras em movimento sem compensação adequada.
- Transmissão RTSP ou monitoramento 24/7 em produção.
- Controle de semáforos ou intervenção automática em tráfego real.
- Garantias de desempenho em condições de segurança crítica.
2.3 Estratégia de evolução
Fase 1: usar pesos YOLO pré-treinados para construir um baseline e validar o pipeline completo.
Fase 2: avaliar o baseline em vídeos anotados, ajustar parâmetros e integrar métricas.
Fase 3 (opcional): realizar fine-tuning do detector em um dataset de tráfego e comparar os resultados com o baseline.
Fase 4 (pesquisa): comparar ByteTrack com outra estratégia (por exemplo, BoT-SORT), sob o mesmo detector e protocolo de avaliação.
Distinção importante: o rastreador ByteTrack é um algoritmo de associação de detecções ao longo do tempo; seu uso não implica treinar uma rede neural do zero. O treinamento/fine-tuning é uma etapa separada, aplicada ao detector, quando necessário.

3. Stack tecnológica
Camada	Tecnologias sugeridas	Papel
Linguagem de CV	Python 3.11+	Processamento e experimentação
Detector	Ultralytics YOLO (versão e pesos fixados no ambiente)	Bounding boxes e classes
Tracking	ByteTrack	Associação temporal de detecções
Processamento de vídeo	OpenCV + FFmpeg/ffprobe	Decodificação, metadados, renderização
Deep learning	PyTorch	Inferência e eventual fine-tuning
Cálculo e dados	NumPy, Pandas	Coordenadas, eventos e estatísticas
Avaliação	TrackEval + ferramentas de detecção	HOTA, IDF1, MOTA e demais métricas
API	FastAPI + Pydantic	Jobs, uploads, resultados e consultas
Execução de jobs	Worker local separado + SQLite	Processamento assíncrono simples no MVP
Frontend	Next.js + TypeScript	Aplicação web
UI	Tailwind CSS + shadcn/ui	Interface profissional
Gráficos	Plotly.js ou Recharts	Evolução temporal, classes, métricas
Testes	Pytest, Vitest, Playwright	Testes unitários, integração e E2E
Qualidade	Ruff, GitHub Actions	Lint, formatação, CI


Licenciamento: o ecossistema Ultralytics oferece uso sob AGPL-3.0 e licença Enterprise. Antes de decidir a licença do repositório ou transformar o sistema em produto fechado, verificar a compatibilidade dos componentes, modelos e obrigações do projeto. Dados de treinamento também possuem termos independentes dos códigos.
4. Arquitetura proposta
                           ┌─────────────────────────┐
                           │   Next.js Web Client    │
                           │ Upload / ROI / Dashboard│
                           └────────────┬────────────┘
                                        │ HTTP
                           ┌────────────▼────────────┐
                           │       FastAPI API       │
                           │  Jobs / Config / Export │
                           └────────────┬────────────┘
                                        │ job metadata
                           ┌────────────▼────────────┐
                           │ SQLite + Local Artifacts│
                           │ Status / Events / Video │
                           └────────────┬────────────┘
                                        │
                           ┌────────────▼────────────┐
                           │    Background Worker    │
                           │ Video Processing Pipeline│
                           └────────────┬────────────┘
                                        │
  Video → Decode → Detect (YOLO) → Track (ByteTrack) → Geometry / Events
                                                        │
                 ┌──────────────────────────────────────┼─────────────┐
                 ▼                                      ▼             ▼
          Annotated Video                         Events CSV      Metrics JSON
                 └──────────────────────────────────────┼─────────────┘
                                                        ▼
                                             Dashboard & Reports
4.1 Separação de responsabilidades
- DetectorAdapter: recebe um frame e devolve detecções normalizadas para um contrato interno.
- TrackerAdapter: recebe detecções em sequência e devolve track_id, caixa, classe e estado.
- TrackHistoryManager: registra pontos de trajetória com limite de memória e timestamps.
- GeometryService: calcula centros inferiores de bounding boxes, cruzamentos, permanência em ROI e coordenadas normalizadas.
- LineCounter: produz eventos de cruzamento por direção e mantém controle de contagem única.
- ZoneAnalytics: calcula entrada, saída e presença por região; tempo de permanência apenas quando os timestamps são confiáveis.
- VisualizationService: renderiza boxes, IDs, linhas, zonas e trajetórias no vídeo.
- MetricsService: agrega contagens, distribuições e indicadores de processamento.
- EvaluationPipeline: compara saída com anotações de referência, sem depender da interface web.
- ArtifactStore: administra vídeos, configurações, metadados, relatórios e limpeza.
4.2 Contrato interno mínimo
from dataclasses import dataclass

@dataclass(frozen=True)
class Detection:
    bbox_xyxy: tuple[float, float, float, float]
    class_id: int
    confidence: float

@dataclass(frozen=True)
class Track:
    track_id: int
    bbox_xyxy: tuple[float, float, float, float]
    class_id: int
    confidence: float | None

@dataclass(frozen=True)
class CrossingEvent:
    video_id: str
    frame_index: int
    timestamp_s: float
    track_id: int
    class_id: int
    line_id: str
    direction: str
Observação: IDs de tracking são válidos apenas dentro de uma execução/vídeo, não identificam permanentemente pessoas ou veículos e podem mudar após oclusões prolongadas.
4.3 Armazenamento
No MVP, usar:
- SQLite: jobs, caminhos de artefatos, status, eventos e metadados.
- Filesystem local: vídeos originais, vídeos anotados e relatórios.
- JSON/YAML: configuração de processamento e experimentos.
O modelo deve permitir trocar o storage futuramente por PostgreSQL e object storage sem reescrever os algoritmos.
5. Módulos funcionais detalhados
Módulo 01 — Video Input & Metadata
Objetivo: receber um vídeo e preparar uma sequência consistente de frames.
Funcionalidades:
- Upload validado de arquivos de vídeo.
- Exibição de resolução, duração, codec e FPS reportado.
- Pré-visualização do primeiro frame para definição de linhas e zonas.
- Seleção de trecho temporal para processar.
- Validação de tamanho, duração, formato e resolução.
- Tratamento de vídeos corrompidos e interrupções de decodificação.
- Registro de timestamp por frame e fallback documentado quando necessário.
- Seleção de resolução de inferência e política de amostragem de frames.
Critérios técnicos:
- Usar dimensões originais como referência para todas as geometrias.
- Preservar a ordem temporal dos frames.
- Diferenciar FPS do vídeo, FPS efetivo processado e FPS de inferência.
- Para vídeos com frame rate variável, preferir timestamps reais aos valores derivados de frame_index / fps.
Saídas: metadados do vídeo, frames/timestamps e configuração de execução.
Módulo 02 — Object Detection
Objetivo: identificar objetos relevantes ao tráfego em cada frame.
Classes inicialmente priorizadas: carro, motocicleta, ônibus, caminhão, bicicleta e pessoa, conforme o mapeamento real do modelo/dataset escolhido.
Funcionalidades:
- Carregar checkpoint compatível do detector.
- Configurar confidence, IoU/NMS, tamanho de entrada e classes permitidas.
- Executar inferência por frame.
- Converter coordenadas da inferência para a resolução original do vídeo.
- Exibir bounding boxes, rótulos e scores.
- Registrar tempo de inferência separado do tempo de decodificação e renderização.
- Permitir troca de checkpoints e comparação controlada de modelos.
Saídas: lista de Detection por frame e logs de desempenho.
Módulo 03 — Multi-Object Tracking
Objetivo: associar detecções entre frames e manter identificadores de trajetória.
Método principal: ByteTrack.
Funcionalidades:
- Integrar ByteTrack por uma interface desacoplada do detector.
- Preservar estado do tracker entre os frames do mesmo vídeo.
- Ajustar limiares de associação e tolerância a tracks perdidos.
- Registrar início/fim de tracks, duração e última observação.
- Identificar mudanças inesperadas de ID para análise posterior.
- Descartar tracks muito curtos conforme regra configurável de análise.
- Reinicializar completamente o tracker ao iniciar outro vídeo ou nova execução.
Parâmetros experimentais:
- track_high_thresh
- track_low_thresh
- new_track_thresh
- track_buffer
- match_thresh
- fuse_score
Saídas: objetos Track e histórico temporal por ID.
Módulo 04 — Line Crossing & Direction Counting
Objetivo: contar objetos ao cruzarem uma linha virtual.
Funcionalidades:
- Desenhar uma ou mais linhas sobre o primeiro frame.
- Salvar endpoints em coordenadas normalizadas, facilitando mudanças de resolução.
- Definir sentido A→B e B→A para cada linha.
- Utilizar um ponto de referência por track, preferencialmente o centro inferior da bounding box para análise de tráfego ao nível do chão.
- Verificar mudança de lado da linha entre observações consecutivas, com uma banda de histerese configurável.
- Exigir tamanho mínimo de track e observações suficientes para aceitar um cruzamento.
- Contabilizar evento apenas uma vez por (job_id, line_id, track_id, direction) no modo de contagem única.
- Armazenar evento com frame, timestamp, classe, linha, direção e track_id.
- Agregar eventos por classe, direção e intervalo temporal.
Tratamento de erros:
- Jitter próximo da linha não deve gerar várias contagens.
- Desaparecimento e reaparecimento podem resultar em novo ID e contagem duplicada; isso deve ser mensurado, não tratado como problema inteiramente resolvido.
- O modo de cruzamento único não permite múltiplas travessias legítimas do mesmo ID na mesma direção; uma versão posterior pode usar uma máquina de estados com rearmamento explícito.
Saídas: eventos CrossingEvent e contagens agregadas.
Módulo 05 — Region of Interest (ROI) & Zone Analytics
Objetivo: medir atividade em áreas delimitadas da cena.
Funcionalidades:
- Desenhar zonas poligonais.
- Detectar quando o ponto de referência de um track entra ou sai de uma zona.
- Calcular quantidade instantânea de tracks ativos dentro da zona.
- Registrar ocupação ao longo do tempo.
- Calcular tempo de permanência aproximado por track usando timestamps.
- Produzir gráficos de ocupação e lista de eventos de entrada/saída.
Limitação: ocupação na imagem não equivale automaticamente a densidade por metro quadrado ou congestionamento real. Para medidas físicas, é necessária calibração e hipóteses adicionais.
Módulo 06 — Trajectory Analysis & Heatmaps
Objetivo: estudar o deslocamento espacial ao longo do vídeo.
Funcionalidades:
- Registrar trajetória (x, y, timestamp) por track_id.
- Renderizar rastro recente no vídeo.
- Exportar trajetórias completas em JSON/CSV.
- Gerar mapa de densidade de observações de tracks na imagem, com parâmetros documentados de acumulação e suavização.
- Filtrar heatmap por classe e janela temporal.
- Visualizar movimentos predominantes em gráficos.
Cuidados metodológicos:
- Heatmaps em coordenadas da imagem são apropriados para câmera fixa; não descrevem automaticamente ocupação geográfica.
- Objetos lentos geram mais observações na mesma região; portanto, distinguir densidade de observações de contagem de passagens únicas.
Módulo 07 — Video Rendering & Export
Objetivo: gerar material visual para análise e portfólio.
Funcionalidades:
- Exibir vídeo original e processado.
- Sobrepor classes, bounding boxes, IDs e trajetórias.
- Renderizar linhas e zonas.
- Mostrar contadores por direção e classe.
- Exportar vídeo anotado em formato amplamente compatível, sujeito aos codecs disponíveis.
- Exportar crossing_events.csv, tracks.csv, summary.json e config.json.
- Disponibilizar arquivos por job concluído.
Critério importante: falha na geração do vídeo anotado não deve apagar os resultados numéricos já produzidos; reportar estados parciais ou erro com clareza.
Módulo 08 — Dashboard & Analytics
Objetivo: apresentar os resultados da inspeção de tráfego.
Telas e gráficos:
- KPI: total de cruzamentos, por direção e classe.
- Série temporal de cruzamentos por minuto (ou intervalo configurável).
- Composição por classe.
- Ocupação por zona.
- Distribuição de duração das tracks.
- Galeria de exemplos de tracks fragmentados, quando identificáveis.
- Latência, FPS efetivo e uso de recursos.
- Comparação entre jobs processados sob configurações diferentes.
Observação: um vídeo com duração pequena pode não comportar agregação por minuto; ajustar granularidade sem inventar valores.
Módulo 09 — Evaluation & Scientific Benchmark
Objetivo: avaliar o sistema em dados anotados e separar erros de detecção, associação e contagem.
Detecção:
- Precision, Recall e mAP@50:95 em dados anotados no formato adequado.
- Análise por classe e por escala de objeto.
Tracking:
- HOTA, IDF1, MOTA e número de ID switches (quando houver ground truth de trajetórias).
- Análise de fragmentação e desempenho sob oclusões.
- Utilizar TrackEval com conversores explícitos de formato de anotação.
Contagem:
- MAE da contagem por vídeo/linha/classe/direção.
- Erro absoluto e relativo, explicitando como lidar com contagem real zero.
- Precision e Recall de eventos de cruzamento quando houver anotações temporais e correspondência de eventos.
Computação:
- Latência média, mediana e p95 por frame.
- FPS de inferência e FPS end-to-end.
- Utilização/peak aproximado de RAM e VRAM.
- Tempo total de processamento e tamanho dos artefatos.
Regra: métricas de tracking como HOTA/IDF1 não são calculáveis de maneira válida somente a partir dos IDs previstos; necessitam identidades anotadas na sequência. Vídeos sem anotações devem ser apresentados como demonstração qualitativa ou requerer anotação de referência.
Módulo 10 — Experiment Tracking & Reproducibility
Objetivo: manter histórico verificável dos resultados.
Registrar em cada execução:
- Identificador e hash do vídeo.
- Detector, hash/versão do checkpoint e conjunto de classes.
- Tracker e parâmetros completos.
- Resolução de inferência, frame sampling e regra temporal.
- Definição normalizada de linhas e zonas.
- Hardware, versões do Python/PyTorch/OpenCV e commit Git.
- Seed, quando aplicável.
- Contagens, métricas, tempo e caminhos dos artefatos.
- Origem e licença do dataset.
Produzir um manifest.json por job com as configurações essenciais para repetição do experimento.
6. Datasets e plano de dados
6.1 Datasets recomendados
Dataset	Aplicação	Observações
VisDrone	Detecção e MOT de veículos/pedestres, especialmente visão aérea	Bom para estender a avaliação, mas cenas com movimento de câmera requerem cuidado na análise de linhas fixas
BDD100K	Trânsito sob condições variadas de clima, luz e ponto de vista	Útil para robustez e tracking; gravações embarcadas não devem ser tratadas como câmera fixa
MOTChallenge	Benchmark de rastreamento, especialmente de pedestres	Adequado para avaliação de identidades e métricas MOT, não necessariamente para contagem viária
AI City Challenge	Vídeos e desafios de análise de trânsito	Conferir dados, objetivos, formatos e condições de uso de cada track


6.2 Estratégia de seleção para o MVP
1. Selecionar 2–3 vídeos de câmera fixa cuja licença permita os testes pretendidos.
2. Garantir cenas com tráfego leve e moderado; buscar ao menos uma cena com oclusões.
3. Criar pequenas anotações manuais de eventos de cruzamento para validar o contador.
4. Reservar vídeos diferentes para ajuste de thresholds e avaliação final.
5. Separar vídeos por sequência/câmera/cena, não frames aleatórios, para evitar vazamento temporal caso haja fine-tuning.
6. Documentar proveniência, permissões e eventuais restrições de redistribuição.
6.3 Dados anotados necessários
- Para avaliar detecção: bounding boxes de referência por frame.
- Para avaliar tracking: bounding boxes com IDs consistentes ao longo de uma sequência.
- Para avaliar contagem: eventos de cruzamento ou contagens verdadeiras por linha, direção e classe.
- Para avaliar robustez: versões perturbadas de vídeos e, preferencialmente, suas referências originais preservadas.
Regra de governança: não subir vídeos de terceiros ao repositório sem licença/permissão apropriada; fornecer links e scripts de preparação. Evitar usar gravações com dados pessoais sem base apropriada e controles de acesso.
7. API e modelo de execução
7.1 API REST inicial
Método	Rota	Descrição
GET	/api/health	Health check
POST	/api/videos	Upload e validação de vídeo
GET	/api/videos/{video_id}	Metadados e frame de preview
GET	/api/models	Modelos/tracker configs disponíveis
POST	/api/jobs	Criar job com vídeo, linhas, zonas e parâmetros
GET	/api/jobs	Listagem e filtros
GET	/api/jobs/{job_id}	Status e progresso
POST	/api/jobs/{job_id}/cancel	Solicitar cancelamento seguro
GET	/api/jobs/{job_id}/summary	Agregações
GET	/api/jobs/{job_id}/events	Eventos de cruzamento paginados
GET	/api/jobs/{job_id}/tracks	Trajetórias/resultados, paginados
GET	/api/jobs/{job_id}/artifacts/{name}	Download de artefatos permitidos
GET	/api/experiments	Comparação de execuções


7.2 Estado do processamento
queued → running → completed
                 ↘ failed
                 ↘ cancelled
Requisitos:
- POST /api/jobs retorna 202 Accepted, job_id e status inicial.
- Worker externo executa a tarefa com isolamento de erros.
- Frontend consulta status periodicamente no MVP; WebSocket/SSE é opcional.
- Job grava progresso (frames processados, etapa atual, erro se ocorrer).
- Reprocessamentos criam novos jobs, não sobrescrevem resultados antigos.
- Cancelamento encerra processamento em um ponto seguro e fecha arquivos.
- Validar que links de download não permitam path traversal.
7.3 Exemplo de configuração de job
{
  "video_id": "video_sample_01",
  "detector": {
    "model_id": "yolo_pretrained_baseline",
    "confidence": 0.25,
    "iou": 0.7,
    "image_size": 640,
    "classes": ["car", "motorcycle", "bus", "truck", "person", "bicycle"]
  },
  "tracker": {
    "type": "bytetrack",
    "config_id": "bytetrack_baseline"
  },
  "processing": {
    "frame_stride": 1,
    "render_annotated_video": true
  },
  "lines": [
    {
      "id": "entry_line",
      "start": [0.20, 0.55],
      "end": [0.82, 0.55],
      "hysteresis_px": 8
    }
  ],
  "zones": [
    {
      "id": "intersection",
      "points": [[0.25, 0.35], [0.80, 0.35], [0.85, 0.85], [0.20, 0.85]]
    }
  ]
}
Parâmetros e identificadores acima são exemplos de contrato, não valores validados como ótimos. A API deverá mapear nomes de classes para IDs de cada checkpoint.

7.4 Exemplo de evento exportado
{
  "job_id": "job_001",
  "video_id": "video_sample_01",
  "frame_index": 348,
  "timestamp_s": 11.6,
  "track_id": 17,
  "class_name": "car",
  "line_id": "entry_line",
  "direction": "A_TO_B",
  "event_type": "line_crossing"
}
8. Interface de usuário
8.1 Direção visual
- Dark mode como padrão, com azul como cor de destaque.
- Aparência de painel técnico/científico, sem excesso de elementos decorativos.
- Tipografia legível, gráficos com unidades e estados de carregamento claros.
- Interface em inglês.
- Prioridade para desktop, com responsividade em tablets.
8.2 Páginas
1. Overview: apresentação, demonstrações, últimos jobs e métricas globais.
2. Video Workspace: upload, pré-visualização, desenho de linhas/zonas, escolha de detector e tracker.
3. Processing Jobs: fila, progresso, sucesso/falha e possibilidade de cancelar.
4. Tracking Viewer: vídeo anotado, timeline, trajetórias e filtros por classe/ID.
5. Traffic Analytics: gráficos de contagem, direção, classe, ROI e heatmaps.
6. Experiment Comparison: comparação lado a lado de configurações e resultados.
7. Methodology / About: descrição da metodologia, datasets, limitações e links para artigos.
8.3 Experiência do fluxo principal
Upload vídeo
  → visualizar primeiro frame
  → configurar linhas e zonas
  → selecionar modelo, tracker e parâmetros
  → iniciar job
  → visualizar progresso
  → assistir vídeo processado
  → consultar gráficos e contagens
  → exportar vídeo + CSV + JSON
UX essencial: o usuário deve conseguir concluir esse fluxo sem editar código Python.
9. Estrutura sugerida do monorepo
intelligent-traffic-tracking/
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── workspace/
│   │   ├── jobs/
│   │   ├── analytics/
│   │   └── experiments/
│   ├── components/
│   ├── features/
│   │   ├── video-upload/
│   │   ├── geometry-editor/
│   │   ├── tracking-viewer/
│   │   └── analytics/
│   ├── lib/
│   └── types/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── storage/
│   │   ├── jobs/
│   │   └── main.py
│   └── tests/
├── vision/
│   ├── detectors/
│   ├── trackers/
│   ├── pipeline/
│   ├── geometry/
│   ├── counting/
│   ├── analytics/
│   ├── rendering/
│   ├── evaluation/
│   ├── datasets/
│   ├── configs/
│   └── tests/
├── experiments/
│   ├── configs/
│   ├── notebooks/
│   └── reports/
├── scripts/
├── docs/
│   ├── architecture.md
│   ├── datasets.md
│   ├── evaluation.md
│   └── methodology.md
├── examples/
│   └── sample_results/
├── .github/workflows/
├── .gitignore
├── README.md
└── LICENSE
Versionamento: excluir datasets/ baixados, vídeos grandes, checkpoints não autorizados, cache e ambientes virtuais. Publicar manifests, configurações e scripts que permitam recuperar ou reproduzir os resultados.
10. Metodologia experimental para portfólio e IC
Experimento A — Impacto dos parâmetros do ByteTrack
Questão: como limiares de associação e track_buffer alteram continuidade de ID e contagem?
Variável independente: configurações do tracker (alterar um fator por vez e depois, se possível, avaliar interações).
Variáveis controladas: detector, pesos, resolução, vídeos, classes e política de amostragem.
Métricas: HOTA, IDF1, ID switches, erro de contagem, latência.
Hipótese: configurações que ajudam a recuperar tracks ocluídas podem reduzir fragmentação, mas podem também elevar associações incorretas em cenas densas.
Experimento B — Densidade e oclusão
Questão: o tracking se degrada quando aumenta a concentração de objetos e a sobreposição?
Desenho: separar vídeos/segmentos anotados em faixas de densidade/oclusão previamente definidas.
Métricas: IDF1, HOTA, ID switches, recall de detecção e erro de contagem.
Análise: verificar em quais condições o sistema perde identidade, omite cruzamentos ou gera duplicações.
Experimento C — Robustez a degradações visuais
Questão: qual é o impacto de degradações visuais na precisão do tracking e da contagem?
Condições: baseline; redução de brilho; desfoque; ruído; compressão (com intensidades explícitas).
Controle: usar as mesmas sequências e manter consistência temporal das transformações; repetir experimentos quando houver aleatoriedade.
Métricas: desempenho de detecção, HOTA/IDF1, erro de contagem e FPS.
Experimento D — Detector baseline vs. detector ajustado (extensão)
Questão: fine-tuning em tráfego melhora significativamente tracking e contagem?
Comparação: pesos pré-treinados vs. detector ajustado com dados de treinamento separados por sequência.
Controle: manter o tracker e seus parâmetros fixos na comparação principal.
Métricas: mAP, Recall, IDF1/HOTA, erro de contagem e inferência.
Experimento E — ByteTrack vs. BoT-SORT (extensão)
Questão: qual algoritmo apresenta melhor equilíbrio entre associação, custo computacional e contagem em cenas distintas?
Controle: mesmo detector, vídeos, classes, limiares de detecção e protocolo de avaliação.
Observação: avaliar separadamente câmera fixa e móvel quando os vídeos disponíveis permitirem.
10.1 Protocolo mínimo de avaliação
1. Definir cenas e anotações de referência.
2. Separar dados de desenvolvimento/validação/teste por sequência.
3. Congelar o conjunto de teste antes de ajustar parâmetros.
4. Documentar software, hardware, modelo, configurações e seeds.
5. Executar o baseline e salvar artefatos.
6. Realizar variações planejadas dos parâmetros.
7. Reportar resultados por sequência e agregados; não apenas a melhor execução.
8. Exibir exemplos visuais de erros e discutir hipóteses de causa.
9. Registrar limitações, viés de seleção de vídeos e condições não testadas.
10. Evitar afirmar superioridade estatística sem análise apropriada e amostra suficiente.
11. Plano de implementação por sprints
Sprint 1 — Foundation & Video Pipeline
- [ ] Inicializar monorepo e ambientes Python/Node.
- [ ] Configurar lint, testes e CI.
- [ ] Implementar leitura de vídeo com metadados e timestamps.
- [ ] Criar CLI para processar um vídeo de teste.
- [ ] Criar contratos internos Detection, Track e CrossingEvent.
- [ ] Gerar vídeo de saída básico sem tracking.
Critério de entrega: vídeo lido e exportado corretamente; metadados e erros de entrada tratados.
Sprint 2 — Object Detection
- [ ] Integrar detector pré-treinado.
- [ ] Filtrar classes relevantes.
- [ ] Converter boxes à resolução original.
- [ ] Renderizar detecções e scores.
- [ ] Instrumentar tempos de inferência.
- [ ] Criar testes do adaptador e das conversões de coordenadas.
Critério de entrega: vídeo com bounding boxes e classes consistentes, além de registro de desempenho.
Sprint 3 — ByteTrack & Trajectories
- [ ] Implementar interface TrackerAdapter.
- [ ] Integrar ByteTrack mantendo estado temporal.
- [ ] Salvar IDs e posições por frame.
- [ ] Renderizar IDs e trajetórias.
- [ ] Tratar desaparecimento e reentrada de objetos.
- [ ] Validar reset do tracker entre execuções.
Critério de entrega: objetos rastreados em vídeos completos, com logs de trajetórias.
Sprint 4 — Counting, Lines & Zones
- [ ] Implementar editor de geometria no preview do vídeo.
- [ ] Criar line crossing com sentido e histerese.
- [ ] Evitar contagens duplicadas por ID/linha/direção no MVP.
- [ ] Implementar regiões poligonais e presença.
- [ ] Exportar eventos CSV/JSON.
- [ ] Testar crossing em sequências sintéticas.
Critério de entrega: contagens auditáveis, com eventos por classe e direção.
Sprint 5 — API, Jobs & Web Application
- [ ] Criar API FastAPI de upload, jobs e resultados.
- [ ] Implementar worker com fila em SQLite.
- [ ] Expor status/progresso e downloads.
- [ ] Criar workspace Next.js para upload e configuração.
- [ ] Construir visualizador do vídeo anotado.
- [ ] Criar dashboard com agregações.
Critério de entrega: execução end-to-end pelo navegador sem comandos manuais.
Sprint 6 — Evaluation & Experiments
- [ ] Criar adaptadores de datasets e formatos de ground truth.
- [ ] Integrar TrackEval para dados anotados.
- [ ] Elaborar anotação manual de eventos de contagem no conjunto de avaliação.
- [ ] Implementar métricas de contagem e latência.
- [ ] Executar Experimentos A, B e C com protocolo fixo.
- [ ] Gerar tabelas, gráficos e exemplos de falhas.
Critério de entrega: relatório comparativo reproduzível com métricas válidas.
Sprint 7 — Quality, Documentation & Portfolio
- [ ] Revisar qualidade do código e cobertura de testes.
- [ ] Escrever README técnico em inglês.
- [ ] Documentar arquitetura, instalação, datasets, modelos e limitações.
- [ ] Adicionar demonstração visual e screenshots autorizados.
- [ ] Gerar vídeo curto explicativo.
- [ ] Revisar licença do software, checkpoints e conteúdos de exemplo.
Critério de entrega: projeto demonstrável, documentado e publicável.
12. Testes obrigatórios
12.1 Testes unitários
- Coordenadas de bounding boxes e normalização.
- Class mapping do detector.
- Linha horizontal, vertical e diagonal.
- Direção correta de cruzamento em ambos os sentidos.
- Track que se aproxima da linha mas não atravessa.
- Jitter próximo da linha sem contagem adicional.
- Track que cruza uma linha uma vez.
- Track que desaparece antes de cruzar.
- Track com coordenadas fora da imagem.
- Polígono de ROI e ponto exatamente na borda (regra definida).
- Contagem separada para duas linhas e classes diferentes.
- Reset de estado entre vídeos distintos.
12.2 Testes de integração
- Vídeo curto → detecção → tracking → contagem → exportação.
- Validação de tipos/tamanhos de upload.
- Falha de decodificação e status de job.
- Worker reiniciado após erro.
- Cancelamento de job.
- Exportação sem perda de eventos.
- Métricas produzidas a partir de formatos de anotação conhecidos.
12.3 Testes E2E
- Fazer upload de vídeo válido.
- Desenhar uma linha e salvar a configuração.
- Iniciar processamento.
- Ver progresso e resultado.
- Abrir vídeo processado.
- Consultar contagem por direção e classe.
- Baixar relatórios.
12.4 Critérios quantitativos
Não estabelecer metas de HOTA/IDF1/FPS sem verificar primeiro o dataset e hardware efetivos. Definir baselines medidos e metas realistas após os primeiros testes. Critérios obrigatórios no MVP: correção determinística dos contadores nos testes sintéticos, exportação íntegra e benchmarks documentados.
13. Requisitos não funcionais
Performance
- Começar com um modelo YOLO leve e resolução moderada.
- Permitir execução em CPU, com GPU quando disponível.
- Medir latência com aquecimento e sincronização de GPU quando necessário.
- Limitar memória de históricos e frames em buffer.
- Evitar carregar vários modelos grandes simultaneamente.
- Relatar diferença entre FPS de inferência e throughput end-to-end.
Segurança e privacidade
- Não implementar reconhecimento facial ou identificação pessoal no MVP.
- Validar arquivo, MIME efetivo, codec, tamanho e duração.
- Limitar exposição dos vídeos enviados e configurar retenção/limpeza.
- Não usar gravações de pessoas/placas em portfólio sem autorização ou tratamento adequado.
- Não inferir identidades reais a partir de track_id.
- Documentar origem dos vídeos e observar LGPD e termos de uso aplicáveis quando pertinente.
Confiabilidade
- Jobs isolados com estados claros.
- Tratamento de vídeos malformados.
- Versionamento das configurações.
- Logs estruturados sem dados pessoais desnecessários.
- Testes automatizados nos algoritmos de contagem.
- Preservação dos resultados parciais quando viável, sem afirmar sucesso de jobs incompletos.
Reprodutibilidade
- Dependências fixadas por lockfile quando aplicável.
- Checkpoint e hash registrados.
- Configurações serializadas.
- Protocolos de validação documentados.
- Registro de hardware e versões.
- Scripts CLI que reproduzam os experimentos sem frontend.
14. Critérios de aceitação do MVP
- [ ] É possível importar um vídeo válido e ver seus metadados.
- [ ] Um checkpoint YOLO compatível detecta as classes selecionadas.
- [ ] ByteTrack produz IDs e trajetórias sem reiniciar a cada frame.
- [ ] O usuário pode desenhar linhas na prévia e definir sentidos.
- [ ] O sistema conta cruzamentos por classe e direção.
- [ ] O sistema evita duplicações decorrentes de jitter nos cenários de teste.
- [ ] Regiões poligonais exibem ocupação baseada em tracks.
- [ ] Vídeo anotado e eventos CSV/JSON são exportados.
- [ ] O dashboard mostra contagens, séries temporais e desempenho.
- [ ] Jobs têm estados e erros visíveis, sem bloquear a requisição HTTP.
- [ ] Há testes automatizados dos componentes críticos.
- [ ] Métricas de tracking são calculadas apenas para sequências com ground truth adequado.
- [ ] Pelo menos três experimentos estão documentados com método e resultados reais.
- [ ] README explica instalação, obtenção dos dados, execução e limitações.
15. Entregáveis finais
1. Aplicação web para upload, configuração, visualização e análise.
2. Pipeline Python reutilizável, independente da interface.
3. Integração YOLO + ByteTrack com parâmetros versionados.
4. Módulo de contagem de cruzamentos e direção.
5. Módulo ROI/trajectories com análise espaço-temporal.
6. Vídeos anotados e relatórios em formatos exportáveis.
7. Benchmark de tracking e contagem com ground truth.
8. Três experimentos documentados com tabelas e figuras.
9. Documentação técnica (arquitetura, decisões e limitações).
10. README e demonstração em vídeo para portfólio.
16. Evolução acadêmica — proposta de IC
16.1 Título provisório
Evaluation of Multi-Object Tracking Robustness and Counting Accuracy in Urban Traffic Videos Under Occlusion and Visual Degradation
Título em português: Avaliação da Robustez do Rastreamento de Múltiplos Objetos e da Precisão da Contagem em Vídeos de Tráfego Urbano sob Oclusões e Degradações Visuais.
16.2 Problema de pesquisa
Como as condições visuais e a continuidade das identidades rastreadas influenciam a precisão de sistemas de contagem automática de veículos e pedestres?
16.3 Hipóteses testáveis
- H1: cenas com mais oclusões aumentam os erros de associação e podem elevar o erro de contagem.
- H2: a configuração dos limiares de associação influencia a relação entre recall, trocas de ID e duplicação de eventos.
- H3: melhorar a detecção não garante melhora proporcional no resultado final de contagem, pois há erros adicionais no tracking e na lógica geométrica.
16.4 Variáveis
Independentes: níveis de oclusão/densidade, degradações visuais, thresholds do detector e tracker.
Dependentes: HOTA, IDF1, ID switches, erro de contagem, recall e FPS.
Controladas: sequências, anotações, região/linha de contagem, resolução, política de frames, hardware, versão dos modelos.
16.5 Potenciais contribuições
- Benchmark reproduzível de contagem e tracking em cenas de tráfego.
- Análise quantitativa da relação entre qualidade do tracking e erro de contagem.
- Discussão de limitações em condições adversas.
- Pipeline modular e scripts abertos que facilitem replicação de estudos.
Nota científica: a existência de uma implementação e de gráficos não garante originalidade suficiente para publicação. A contribuição de pesquisa deverá ser refinada com o orientador após revisão bibliográfica e análise do estado da arte.
17. Configuração inicial sugerida para o hardware
Hardware de referência: notebook com Intel Core i5 13ª geração, RAM 16 GB e NVIDIA RTX 3050 6 GB; sistema Fedora Linux.
Item	Ponto de partida
Detector	Variante leve do YOLO compatível com a versão instalada
Resolução de inferência	640 px no maior lado/imgsz equivalente, sob ajuste
Batch de inferência	1 (processamento sequencial)
Rastreador	ByteTrack
Quantidade de fontes	1 vídeo por job
Política temporal	Processar todos os frames na primeira baseline
Exportação	MP4 anotado + CSV + JSON
Avaliação	Vídeos curtos com referência antes de escalar


Os valores servem para iniciar testes; latência, memória e qualidade precisam ser medidos no hardware real. A execução local deve funcionar antes de qualquer tentativa de publicação/deploy em nuvem.
18. Ordem de prioridade e definição de pronto
P0 — Núcleo científico/funcional
- Processamento de vídeo por CLI.
- Detecção + ByteTrack.
- Trajetórias e eventos de cruzamento.
- Contagem validada com testes.
- Exportação dos resultados.
P1 — Portfólio e análise
- API de jobs.
- Web workspace e visualizador.
- Dashboard de analytics.
- Comparações quantitativas e avaliação com ground truth.
P2 — Pesquisa avançada
- Fine-tuning do detector.
- Comparação ByteTrack vs. BoT-SORT.
- Robustez com transformações controladas.
- Câmera móvel com compensação adequada.
- Aceleração/otimização de inferência (ONNX/TensorRT, quando compatível).
Definição de pronto: não basta o vídeo “parecer correto”. A implementação só será considerada pronta após testes de contagem, exports íntegros, resultados quantificados em referências anotadas e documentação reproduzível.
19. Referências técnicas e científicas
1. Ultralytics — Multi-Object Tracking: https://docs.ultralytics.com/modes/track/
2. Ultralytics — Tracker ByteTrack configuration: https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/trackers/bytetrack.yaml
3. ByteTrack (ECCV 2022): https://www.ecva.net/papers/eccv_2022/papers_ECCV/html/315_ECCV_2022_paper.php
4. ByteTrack — repositório de referência: https://github.com/FoundationVision/ByteTrack
5. TrackEval — HOTA, IDF1 e MOTA: https://github.com/JonathonLuiten/TrackEval
6. VisDrone dataset: https://github.com/VisDrone/VisDrone-Dataset
7. BDD100K dataset: https://github.com/bdd100k/bdd100k
8. AI City Challenge — Data Access: https://www.aicitychallenge.org/ai-city-challenge-dataset-access/
9. Ultralytics — Licenciamento: https://www.ultralytics.com/license
Ao publicar pesquisas, citar os trabalhos científicos e datasets efetivamente utilizados, não apenas as bibliotecas de software.
20. Orientações para um agente de implementação (Codex)
Implementar este projeto de forma incremental, começando pelo núcleo Python, depois pela avaliação e por último pela aplicação web. Não substituir a metodologia científica por um dashboard apenas visual. Não inventar resultados de benchmarks, requisitos de performance ou datasets. Manter detector, tracker, contadores e renderização desacoplados. Garantir testes unitários das regras de crossing, pipeline CLI reproduzível e documentação atualizada a cada sprint. Em cada sprint, entregar código executável, testes, instruções de execução, decisões técnicas e limitações observadas. Não iniciar treinamento customizado até existir um baseline integrado e mensurado.