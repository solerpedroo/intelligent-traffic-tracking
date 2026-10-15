# Modelo baseline, dependências e proveniência

Estado da Onda 2, verificado em 2026-10-15. A avaliação científica com ground
truth continua na Onda 7; estes registros comprovam integração e reprodução.

## Checkpoint selecionado

- ID: `yolo11n-coco`, tarefa de detecção, variante nano de YOLO11.
- Fonte: [release oficial de assets v8.3.0](https://github.com/ultralytics/assets/releases/tag/v8.3.0).
- Arquivo: [yolo11n.pt](https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt).
- Tamanho: 5.613.764 bytes.
- SHA-256 fixado: `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`.
- Origem do hash: calculado sobre o download HTTPS da release oficial nesta
  implementação. A API GitHub consultada não publicou digest para esse asset;
  não apresentar este hash como assinatura ou checksum fornecido pelo autor.
- Classes: 80 nomes COCO, verificados contra `model.names` do checkpoint.
  Fonte do mapa: [coco.yaml da versão fixada](https://github.com/ultralytics/ultralytics/blob/v8.4.177/ultralytics/cfg/datasets/coco.yaml).
- Subconjunto inicial: person=0, bicycle=1, car=2, motorcycle=3, bus=5, truck=7.

Definição completa em `vision/configs/catalog.json`. Catálogo não significa
checkpoint presente: obter pesos é uma ação explícita via `prepare-model`.
O adapter verifica tamanho e SHA-256 antes de carregar o arquivo local; arquivos
arbitrários ou modificados não são aceitos. Não há download automático na inferência.

## Dependências e termos consultados

`ultralytics-opencv-headless==8.4.177` é a variante headless indicada na
[documentação oficial de instalação](https://docs.ultralytics.com/quickstart/),
com a mesma API. Evita instalar duas distribuições OpenCV com o mesmo módulo cv2.
PyTorch 2.14.1+cpu e torchvision 0.29.1+cpu vêm do índice CPU oficial via uv;
o lockfile registra a resolução exata. O núcleo básico não depende desses pacotes.

Ultralytics informa [AGPL-3.0 ou Enterprise](https://www.ultralytics.com/license)
para seu ecossistema e pesos. A integração local não atribui automaticamente
uma LICENSE ao monorepo nem decide condições de distribuição/deploy; a revisão
do conjunto efetivamente distribuído permanece no gate final do projeto.
Os termos de datasets e imagens de exemplo são independentes dos algoritmos.

## Preprocessamento, parâmetros e coordenadas

Configuração resolvida vem de `DetectorConfig`; o catálogo expõe os mesmos
defaults. Baseline: imagem 640, confidence 0.1, IoU/NMS 0.7, CPU, FP32, um
thread, batch 1, duas chamadas de warm-up e seed 0. Não são parâmetros ótimos
nem metas de desempenho. `max_detections=300` limita a saída por frame.

O adapter faz resize linear e padding BGR `(114,114,114)` para canvas quadrado.
As escalas x/y usam as dimensões inteiras realmente redimensionadas, incluindo
arredondamento. O SDK recebe esse canvas e devolve boxes em suas coordenadas;
o adapter valida `orig_shape`, remove padding e inverte cada escala uma vez.
Boxes são limitadas à imagem original; caixas totalmente no padding são omitidas.
Não aplicar uma segunda inversão de letterbox do SDK às coordenadas finais.

`visualization_confidence=0.25` filtra apenas desenho. `detections.csv` conserva
as detecções a partir do confidence de entrada, incluindo valores mais baixos.
O limiar de entrada deve ser conciliado com `track_low_thresh` na Onda 3;
esta onda não implementa a associação ByteTrack.

## Tempos e reprodução

`manifest.json` registra run_id, hash do vídeo/checkpoint, classes completas,
configuração, seed, versões instaladas, hardware, commit e estado Git. Os campos
novos são aditivos ao schema 1.0; snapshots anteriores usam os defaults. Fora
de um checkout Git, commit pode ser `null` e dirty é conservadoramente verdadeiro.
O manifest inicial existe antes de carregar o detector; erros são descritos em
`failure.json`. `finished_at` indica término, não sucesso isoladamente.

`timings.csv` registra por frame selecionado: decode/conversão BGR,
letterbox, chamada predict, forward reportado pelo SDK, normalização e transferência
de boxes, desenho e submissão ao encoder. A chamada predict inclui preprocessamento
interno do SDK e NMS; por isso não equivale ao tempo de forward. O warm-up está
separado. Em CUDA, sincronizar antes/depois de predict; caminho GPU requer runtime
compatível e não pode ser alegado como testado sem dispositivo real.

O tempo end-to-end inclui carregamento e warm-up; o flush final do encoder está
nesse tempo total, não no tempo de submissão por frame. Estatísticas de inferência
usam apenas frames processados depois de warm-up. Não somar forward a predict
como se fossem etapas disjuntas: forward é parte da chamada predict.

## Smoke e fronteira científica

O exemplo positivo é [bus.jpg do repositório oficial fixado](https://github.com/ultralytics/ultralytics/blob/v8.4.177/ultralytics/assets/bus.jpg),
SHA-256 `c02019c4979c191eb739ddd944445ef408dad5679acab6fd520ef9d434bfbc63`,
137.419 bytes. Download só com `--download-example`; também é possível fornecer
uma imagem local com `--image`. O asset não é incluído no Git ou redistribuído
como material de portfólio; a página de origem não foi tratada como uma autorização
separada para publicar essa fotografia.

`scripts/smoke_detector.py` repete uma imagem em quatro frames de vídeo e registra
a proveniência. Detectar bus/person demonstra integração, não tracking, diversidade
temporal, precisão ou qualidade de contagem. Observações repetidas não são
objetos únicos. Não há GT nesse smoke; não produzir mAP, HOTA ou IDF1 a partir dele.

Testes `-m detector` exigem assets locais e falham explicitamente se faltarem.
Incluem formatos retrato/paisagem, bounds nas coordenadas originais e entrada
vazia. Durante esses testes, conexões de rede são bloqueadas para confirmar
execução local. A suíte leve usa casos determinísticos e adapters de fixture
identificados; não apresenta suas saídas como resultados de YOLO real.
