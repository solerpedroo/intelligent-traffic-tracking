# Análise do escopo

Data: 2026-10-15. Fonte: [project-scope.md](project-scope.md), versão 1.0.
Esta análise interpreta o escopo; não representa funcionalidades implementadas.

## Ideia central

Construir uma plataforma de análise de vídeos de trânsito de câmera fixa que
transforme detecções em trajetórias, eventos auditáveis e indicadores de fluxo.
O diferencial está na relação mensurável entre qualidade da detecção,
continuidade de identidade e precisão da contagem. Bounding boxes e dashboard
são formas de inspeção; a evidência vem dos testes e das referências anotadas.

## Pilares de desenvolvimento

1. **Núcleo temporal independente.** Python executável por CLI, com adaptadores
   de detector e tracker, processamento sequencial, timestamps explícitos e
   memória limitada. FastAPI e Next.js consomem esse núcleo.
2. **Geometria e contagem corretas.** Linhas finitas, direção inequívoca,
   histerese, deduplicação por execução e ROI com política de borda testada.
3. **Evidência científica.** Avaliar detecção, associação, contagem e custo
   computacional separadamente. HOTA/IDF1 exigem identidades de referência;
   trocas de ID não podem ser afirmadas apenas olhando as predições.
4. **Reprodutibilidade e dados.** Configuração resolvida, hashes, versões,
   hardware, commit, anotações e protocolo registrados por execução. Separação
   de dados por sequência/câmera/cena, antes do ajuste de parâmetros.
5. **Execução confiável.** API curta, worker separado, SQLite e artefatos locais;
   cancelamento, recuperação de falhas e resultados parciais explícitos.
6. **Produto demonstrável.** Editor de linhas/zonas, progresso, vídeo, analytics
   e exports acessíveis no navegador. Interface em inglês; documentação em português.
7. **Continuidade de engenharia.** Ondas com critérios verificáveis, tarefas
   delimitadas, decisões registradas e contexto reutilizável por Cursor e Codex.

## O que aproveitar do repositório de referência

Referência local consultada: `computer-vision-processing-lab`, especialmente
`AGENTS.md`, `docs/implementation-plan.md`, `docs/agent-playbook.md`,
`docs/agentic/` e `.cursor/rules/`.

- Ondas sequenciais, critérios de pronto, cartões de tarefa e workboard.
- Registro de decisões arquiteturais e handoffs factuais para trabalho incompleto.
- Separação entre algoritmos, transporte HTTP e apresentação.
- Regras específicas por área e verificação proporcional ao risco.

As adaptações são essenciais: processamento de vídeo mantém estado entre frames;
há persistência por job, diferenças entre tempo de mídia e tempo de execução,
pesos de modelos, avaliação MOT e resultados parciais. O registry de operações
de imagens vira um catálogo de modelos e configurações; não se copia o modelo
de requisição síncrona ou a política de descartar uploads ao final da requisição.
Os papéis de planejamento, implementação, testes e revisão podem ser exercidos
sequencialmente pelo mesmo agente; não dependem de subagentes instalados.

## Pontos que o plano precisa resolver

- **Ordem de entrega:** a seção 11 coloca a web antes da avaliação, mas a
  orientação final da seção 20 pede núcleo → avaliação → web. O plano adota
  essa última ordem; as sprints representam agrupamentos, sem prazo prometido.
- **Experimento C:** aparece entre os três experimentos mínimos e também na
  prioridade P2. A versão controlada mínima de A/B/C pertence à aceitação do
  MVP; estudos ampliados de robustez ficam para evolução.
- **Direção A/B:** os endpoints da linha não bastam para definir lados. Fixar
  sinal orientado e nomes dos lados, com exemplos na interface.
- **Linha infinita versus segmento:** mudança de lado fora dos endpoints não
  pode contar como travessia da linha desenhada.
- **Baixa confiança:** preservar detecções necessárias à segunda associação
  do ByteTrack; limiares de visualização não podem removê-las prematuramente.
- **Identidades:** um novo ID após oclusão pode duplicar contagem. Deduplicação
  local não resolve reidentificação. Sem ground truth, reportar apenas indícios.
- **Tempo e amostragem:** planejar PTS/VFR e a relação entre frame_stride e
  envelhecimento do tracker. A primeira baseline processa todos os frames.
- **Falha de renderização:** manter resultados numéricos e informar o artefato
  ausente sem afirmar sucesso do vídeo.
- **Dados:** selecionar fontes e referências cedo; não deixar descoberta de
  datasets e anotações para o fechamento do projeto.
- **Implantação:** execução local é pré-requisito. Hospedagem e GPU em nuvem
  não são compromisso automático herdado do outro projeto.

## Limites e decisões ainda pendentes

Permanecem fora do MVP: velocidade física sem calibração, placas/rostos,
identidade persistente, RTSP/24×7, múltiplas câmeras e intervenção no trânsito.
Fine-tuning e comparação com BoT-SORT dependem do baseline medido.

Versões exatas, checkpoint, implementação concreta de ByteTrack, fonte dos
timestamps, codecs, limites de upload e dados de avaliação devem ser validados
nas ondas correspondentes. A análise é documental: não foram executados
benchmarks, verificados termos externos ou selecionados datasets definitivos.

Próxima execução: [Onda 0](agentic/tasks/wave-0-foundation.md), conforme o
[plano de implementação](implementation-plan.md).
