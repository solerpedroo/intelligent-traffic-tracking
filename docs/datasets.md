# Dados e anotações — plano inicial

Atualizado em 2026-10-15. A Onda 1 identifica fontes, permissões publicadas e
protocolo de preparação. Não foram baixados vídeos reais, aceitos contratos de
acesso ou produzidas anotações reais nesta etapa. Fixtures sintéticas verificam
software; não são benchmark científico ou evidência de qualidade em trânsito.

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
