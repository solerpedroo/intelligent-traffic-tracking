# Dados e anotações — plano inicial

Atualizado em 2026-10-15. A Onda 1 identifica fontes, permissões publicadas e
protocolo de preparação. Na Onda 1 não foram baixados vídeos reais nem aceitos
contratos de acesso. A Onda 4 acrescentou um exemplo público local de crossing,
com anotação visual de desenvolvimento, documentado ao final. Fixtures e piloto
não são benchmark científico nem evidência de qualidade geral em trânsito.

## Fonte selecionada para o primeiro piloto

O [Stanford Drone Dataset, dos autores](https://cvgl.stanford.edu/projects/uav_data/)
contém cenas de campus com pedestres, bicicletas e veículos, e publica licença
[CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/).
A página identifica diferentes cenas e disponibiliza vídeos/anotações; o pacote
completo é grande. O uso inicial proposto é pesquisa não comercial, com atribuição
e preservação dos termos. Não copiar vídeos ou thumbnails para o Git ou portfólio
como consequência automática de poder executar testes localmente.

Referência a citar: Robicquet, Sadeghian, Alahi e Savarese, *Learning Social
Etiquette: Human Trajectory Prediction In Crowded Scenes*, ECCV 2016.

Seleção inicial de candidatos, ainda a inspecionar no arquivo oficial:

- **SDD-NEXUS-0:** `nexus/video0`, grupo de cena `nexus`, desenvolvimento/ajuste.
  É candidato a exemplo com veículos; não se presume quantidade de carros.
- **SDD-DEATHCIRCLE-0:** `deathCircle/video0`, grupo `deathCircle`, validação.
  Inspecionar mistura de classes e oclusões antes de definir linhas.
- **SDD-GATES-0:** `gates/video0`, grupo `gates`, teste reservado.
  Nenhum threshold deve ser ajustado com seus resultados.

São slots planejados, não vídeos já preparados ou splits congelados. No recebimento,
confirmar caminhos/IDs no arquivo e rejeitar trechos com deslocamento da câmera,
rotação, geometria instável ou qualidade incompatível com a contagem em linhas
fixas. A origem aérea não garante câmera fixa. Uma seleção reprovada deve ser
substituída antes do congelamento; todos os vídeos da mesma cena ficam no mesmo
grupo, mesmo que seus IDs de sequência sejam diferentes.

O piloto não representa todo trânsito urbano: classes como caminhão e motocicleta
podem não estar cobertas, e a proporção de veículos pode ser pequena. Não mapear
`cart` ou `skater` automaticamente para classes COCO. O class mapping real e as
classes ignoradas serão definidos com os adapters de detecção/avaliação.

## Fonte adicional para trânsito veicular

[UA-DETRAC, página de um dos autores](https://sites.google.com/view/daweidu/projects/ua-detrac)
é candidato para ampliar veículos, boxes, trajetórias e condições de oclusão.
A página fornece links de imagens/anotações e referência científica. Os termos
de acesso/redistribuição precisam ser confirmados na fonte efetivamente obtida
antes de uso; não atribuir ao dataset a licença do código de um mirror.
Não foi selecionado como dado autorizado já preparado nesta onda.

BDD100K e VisDrone não são substitutos automáticos: câmera móvel invalida linhas
fixas sem compensação. MOTChallenge pode servir para MOT, sem comprovar contagem
viária nas mesmas cenas. BrnoCompSpeed não é dependência do MVP: seu repositório
oficial orienta solicitar acesso e descreve um conjunto muito maior que o piloto.

## Preparação e inventário obrigatório

1. Obter dados na fonte oficial; registrar URL final, data, termos e atribuição.
   Verificar espaço disponível antes de baixar o arquivo completo.
2. Guardar originais fora do Git, em raiz local configurável. Registrar SHA-256
   original e de cada arquivo preparado, sequência, cena, classes e anotações.
3. Inspecionar estabilidade de câmera, geometria, resolução, FPS e PTS.
   Converter MOV/imagens para MP4 é uma preparação explícita; o decoder do MVP
   aceita MP4. Essa conversão de datasets ainda não foi implementada.
4. Preservar alinhamento frame↔anotação: registrar offset, resize, seleção,
   time base e qualquer frame removido/duplicado. Não converter por FPS médio
   ou descartar frames silenciosamente. Anotações precisam acompanhar a transformação.
5. Preparar trechos curtos, inicialmente até 60 s; configurar limites do CLI
   explicitamente quando a resolução original exceder o envelope padrão.
6. Confirmar grupos por cena e versionar inventário/splits antes do ajuste
   quantitativo. Congelar o teste antes da Onda 7. Não dividir frames aleatórios.

`examples/dataset-plan.json` registra os slots e a fonte; os hashes permanecem
`null` até aquisição real. Nenhum hash, duração, densidade ou resultado é inventado.

## Referências por tipo de avaliação

- **Detecção:** boxes e classes revisadas nos frames avaliados. Documentar
  cobertura, objetos ignorados e mapeamento para o checkpoint.
- **MOT:** boxes com IDs temporais consistentes; confirmar frames indexados,
  flags de oclusão/ausência e formato no adaptador da Onda 7.
- **Contagem:** anotar manualmente crossing por linha/classe/sentido e instante.
  Começar na Onda 4. Registrar endpoints normalizados, convenção A/B, frame
  original, timestamp, ID de referência quando disponível e incerteza temporal.
- **Eventos/zonas:** entrada/saída e borda seguem as regras implementadas;
  ausência/oclusão não vira saída geométrica por suposição.

Revisar ambiguidades e, quando possível, realizar segunda revisão independente.
Fixar tolerância de pareamento antes de avaliar predições. Intervalos sem eventos
são válidos; erro relativo com GT zero não pode dividir por zero. Só produzir
HOTA/IDF1/ID switches confirmados com referência adequada, nunca apenas com IDs previstos.

## Estado e gates futuros

- Onda 1: fontes e permissões publicadas identificadas; fixtures próprias CFR/VFR
  executáveis e plano de aquisição/anotação definido.
- Antes do baseline real/Onda 4: obter o piloto, auditar câmera e documentar
  arquivos/termos/hashes; anotar eventos no conjunto de desenvolvimento.
- Antes da Onda 7: GT convertido e validado, split de teste congelado, tolerâncias
  e classes definidas. Se faltar referência, bloquear o gate científico e
  apresentar demos apenas como qualitativas.

Em 2026-10-16 o baseline passou a usar o MOT15 oficial, não o Stanford Drone
Dataset. O zip local tem SHA-256
`4197530e8bff30fc9fb55565280b8235ab3cc9d16a2eca3ba95e7d5dcae3a5b4`.
O teste congelado é `MOT15-PETS09-S2L1`. Os resultados estão em
[evaluation.md](evaluation.md). O piloto de vehicles não entrou nesse teste.

Na mesma data, a página oficial
[cvgl.stanford.edu/projects/uav_data](https://cvgl.stanford.edu/projects/uav_data/)
ainda aponta o pacote de cerca de 69 GB para
`http://vatic2.stanford.edu/stanford_campus_dataset.zip`, sob CC BY-NC-SA 3.0.
O nome `vatic2.stanford.edu` resolve para `171.64.68.58`. Duas tentativas de
conexão, em HTTP e HTTPS, expiraram após 20 s e 15 s, sem cabeçalho de
resposta. Não houve download parcial, hash nem auditoria de câmera. Espelhos
de terceiros não foram usados.

## Piloto local de crossing — Onda 4

Em 2026-10-15 foi obtido localmente o exemplo público
[VEHICLES publicado pelo Supervision](https://supervision.roboflow.com/latest/assets/),
[arquivo de vídeo](https://media.roboflow.com/supervision/video-examples/vehicles.mp4).
Essa é uma amostra de desenvolvimento adicional; SDD e seus splits planejados
continuam pendentes, sem substituição pelo exemplo.

- Fonte: 35.345.757 bytes, 3840×2160, 25 fps, 538 frames;
  SHA-256 `ac81100d9310bd4e9c02bc0b13b6492781d009742ced347766b2601be3c44ad4`.
- Auditoria visual local: câmera fixa sobre rodovia, dois sentidos de tráfego;
  150 primeiros frames derivados para 1280×720 sem alterar cadência, seis segundos.
  Não afirmar densidade física, cobertura geral de classes ou qualidade MOT.
- Segmento apenas na pista de aproximação; três veículos observados atravessando,
  dois carros e um caminhão. Rótulos visuais pelo agente em
  [manual-events.json](../examples/counting/manual-events.json); endpoints e controles
  em [lines.json](../examples/counting/lines.json). Frente do carro branco parcialmente
  ocluída, intervalo temporal mais amplo. Não há IDs anotados de referência MOT.
- Download/derivação explícitos por scripts/smoke_counting.py; hashes efetivos de
  fonte/derivação/anotação/config em provenance.json. Eventos matched por classe,
  linha, sentido e intervalo visual, sem tuning posterior neste piloto.
- A documentação pública oferece o asset para exemplos; uma licença específica
  do vídeo não foi estabelecida nesta sessão. Não atribuir automaticamente a
  licença do código Supervision ao conteúdo. Manter fonte, derivados e thumbnails
  locais, ignorados pelo Git; redistribuição/uso de portfólio exige auditoria dos
  direitos. Não aceitar termos em nome do usuário nem inferir licença irrestrita.
- Este piloto permite verificar o fluxo real de crossing; não satisfaz o gate
  científico de dados/GT/splits da Onda 7. Nenhum resultado de acurácia geral ou
  ID switch confirmado decorre dos três eventos. Ver [contratos](counting.md).
