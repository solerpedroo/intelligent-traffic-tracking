# Tarefa: `wave-3-tracking`

- Estado: done
- Onda: 3 — ByteTrack e trajetórias
- Responsável / ferramenta: Codex
- Requisitos do escopo: M03 e M06 parcial
- Dependência: [wave-2-detection](wave-2-detection.md), concluída com evidências.
- Arquivos permitidos: vision/trackers/, vision/configs/, vision/contracts/, vision/pipeline/, vision/rendering/, vision/tests/, arquivos de dependências/lockfiles, docs/architecture.md. Também este cartão, workboard e ADRs relevantes. Escopo ampliado para README, AGENTS, docs/tracking.md, índice dos cartões, inventário de modelos, plano, scripts e CI: comandos reproduzíveis e estado de fechamento.
- Plano: [implementation-plan.md — Onda 3](../../implementation-plan.md).

## Objetivo verificável

Associar detecções temporalmente com estado isolado e trajetórias persistidas.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

## Critérios de pronto

- [x] Implementação concreta de ByteTrack e compatibilidade de thresholds registradas.
- [x] Reset, frames vazios, política de classe e unidade de buffer definidos.
- [x] Rastros limitados em RAM e trajetórias completas em streaming.
- [x] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Usar tracker real com sequências controladas: continuidade, oclusão curta, baixa confiança, buffer, frames vazios e reset. Sem GT não afirmar ID switches confirmados.

Comandos e resultados executados estão registrados abaixo.

## Fora desta tarefa

Reidentificação persistente, novo tracker e métricas MOT sem referência.

## Evidências e revisão

Implementado em 2026-10-15. Revisão exercida sequencialmente pelo Codex.

- ByteTrack Ultralytics headless 8.4.177 + LAP 0.5.13, extra detector e uv.lock.
- TrackerConfig validado e preset no catálogo; CLI `--tracker` e JSON parcial
  `--tracker-config`. Manifest registra implementação, unidade do buffer, classe,
  parâmetros efetivos e versões; detector confidence <= low obrigatório.
- Reset por execução, IDs independentes entre instâncias; frames vazios avançam
  estado, expiração anterior à associação e classe inicial fixa. Observed usa a
  detecção associada; lost é estimativa sem confiança, excluída das trajetórias.
- Histórico por ID com deque limitada, descarte de IDs encerrados e teto de tracks
  vivas com erro explícito. CSV de trajetórias e lifetimes incremental, início e
  última observação, span/censura e elegibilidade configurável de tracks curtas.
- Vídeo com IDs e rastros; não conecta lacunas. Tracking tem timing separado.
- CI manual estendida com testes reais e smoke de tracking; suíte leve sem Torch
  permanece padrão. Nenhuma execução de CI remota foi efetuada nesta sessão.

### Comandos e resultados

Ambiente local: `/tmp/traffic-uv/uv` (uv não está no PATH), `.venv` Python 3.12.15;
ambientes isolados Python 3.14.8 em /tmp. Sem GPU disponível.

```bash
/tmp/traffic-uv/uv sync --extra api --extra video --extra detector
.venv/bin/ruff check vision backend scripts
.venv/bin/ruff format --check vision backend scripts
.venv/bin/pytest
.venv/bin/pytest -m 'tracker or detector'
/tmp/traffic-py314/bin/pytest
/tmp/traffic-detector314/bin/python -m pytest -m 'tracker or detector'
git diff --check
```

- Suíte leve: **140 passed**, 13 deselected, em Python 3.12 e 3.14.
- Integração real: **13 passed**, 140 deselected, em ambas versões. Dez casos
  de ByteTrack e três de YOLO real. Tracking bloqueia conexões de rede.
- Cobertura nova: weak association, início/confirmacão, oclusão curta, empty
  frames, limite inclusivo/expiração, VFR, classe estável, reset/instâncias
  intercaladas, ordem inválida, limite vivo e falha parcial. Sequência com 4.404
  updates verifica limites dos pools; histórico escreve todos os 101 pontos
  enquanto mantém apenas três por ID. Teste visual verifica pixels do rastro e
  ausência de segmento em lacuna, além de não mutar o frame original.
- Ruff lint/formatação e whitespace: aprovados. Wheel/sdist construídos por
  `uv build`; wheel instalada em /tmp/traffic-core-wave0 e verificada com
  Python -I: preset empacotado, nenhuma dependência Torch/av/cv2/lap/FastAPI,
  erro `missing_detector_extra` claro ao tentar instanciar tracker sem extras.

```bash
.venv/bin/python scripts/smoke_detector.py --checkpoint checkpoints/yolo11n.pt \
  --image data/detector-smoke-bus.jpg --tracker bytetrack-default \
  --output-dir artifacts/wave-3-verified-smoke
.venv/bin/traffic-video process artifacts/wave-3-tracking-smoke/source-fixture.mp4 \
  --model yolo11n-coco --checkpoint checkpoints/yolo11n.pt --classes bus \
  --tracker bytetrack-default --tracker-config artifacts/wave-3-cli-params.json \
  --output-dir artifacts/wave-3-cli-smoke
```

- Smoke real CPU final: quatro frames, **5 tracks confirmadas e 20 observações**,
  IDs presentes do primeiro ao último frame. Artefatos em
  `artifacts/wave-3-verified-smoke/result/`; MP4 reaberto e quatro frames
  decodificados. `overlay-preview.png` inspecionado visualmente: boxes e IDs legíveis.
- CLI real com bus e overrides buffer=2/history=3/min_observations=2: uma track,
  quatro observações; parâmetros resolvidos registrados corretamente.
- Assets/artefatos locais ignorados no Git, sem redistribuição de exemplo/pesos.
  O SDK emite aviso de depreciação de `half`; inferência conclui e testes passam.

### Revisão e limites

Diff revisado: contratos/catálogo sem import científico pesado, bounds e PTS
preservados, filtro visual independente do tracker, IDs sem estado global,
nenhuma retenção de todas as trajetórias em RAM, fechamento dos CSVs em falha e
publicação apenas após sucesso. Ajustes encontrados e corrigidos: expiração
upstream após matching, mensagem de dependência ausente, fechamento dos arquivos
nos testes e validação do tipo do JSON de overrides. Nenhum bloqueador restante.

Smoke usa imagem repetida e sequências controladas usam detecções sintéticas.
Não há benchmark de trânsito real, HOTA/IDF1 ou ID switches confirmados sem GT.
Associação agnóstica pode errar entre classes; congelar classe pode preservar erro
inicial. Kalman usa passo de frame, não dt variável. `removed` não distingue
expiração de deduplicação. Falha somente de render com preservação/publicação
numérica independente é responsabilidade da Onda 6. GPU, CI remota e frontend
(não alterado) não foram executados. Dados reais permanecem pendentes.

Próxima ação: Onda 4 — linhas finitas, direção e contagem auditável.

## Contratos afetados (antes da implementação)

TrackerConfig e preset no catálogo; TrackerAdapter com update/reset; estados observed/lost, classe inicial fixa por ID, histórico limitado e CSV incremental. ByteTrack Ultralytics 8.4.177; buffer em frames, associação agnóstica à classe, thresholds validados contra o detector. ADR-010 registra detalhes e limitações.
