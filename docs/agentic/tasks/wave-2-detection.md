# Tarefa: `wave-2-detection`

- Estado: done
- Onda: 2 — Detector YOLO e baseline
- Responsável / ferramenta: Codex / implementação e revisão sequencial
- Requisitos do escopo: M02, §§3, 17
- Dependência: [wave-1-video-cli](wave-1-video-cli.md), concluída com evidências.
- Arquivos permitidos: vision/detectors/, vision/configs/, vision/pipeline/, vision/rendering/, vision/tests/, arquivos de dependências/lockfiles, docs/architecture.md, README.md. Também este cartão, workboard e ADRs relevantes. Contratos, scripts de smoke, CI e documentos de estado serão atualizados para suportar a configuração real de inferência e suas evidências.
- Plano: [implementation-plan.md — Onda 2](../../implementation-plan.md).

## Objetivo verificável

Integrar detector real e renderizar classes/boxes nas coordenadas originais.

## Contratos e decisões

Seguir [AGENTS.md](../../../AGENTS.md), [ADRs](../architecture-decisions.md)
e a seção 5 do plano. Antes de código, declarar contratos afetados e decisões
pendentes. Este cartão pode ser dividido; a onda só fecha com todas as entregas.

Escolhas registradas em ADR-009. DetectorConfig e campos aditivos de manifest
(class_mapping) preservam leitura de snapshots anteriores. ProcessingConfig mantém
copy-only quando model_id é omitido. CLI tem preparação explícita de pesos.

## Critérios de pronto

- [x] Checkpoint/versionamento/hash e class mapping registrados.
- [x] Adapter, thresholds e inversão de resize/letterbox testados.
- [x] Smoke real CPU, manifest e timings separados.
- [x] Validação executada, documentação atualizada e revisão registrada.

## Validação planejada

Boxes em múltiplas proporções, classes inválidas, saída vazia e smoke com checkpoint real. Registrar preparação de pesos e separar esse teste da CI leve.

Comandos executados e resultados registrados abaixo. Smoke real separado
da suíte leve; fixture repetida não é benchmark de tráfego.

## Fora desta tarefa

Tracking, fine-tuning, metas de FPS e comparação de modelos sem protocolo.

## Evidências e revisão

Validação local em 2026-10-15. Python 3.12.15 e 3.14.8; uv 0.13.1;
Ultralytics headless 8.4.177; torch 2.14.1+cpu; torchvision 0.29.1+cpu.
uv foi usado a partir de `/tmp/traffic-uv/uv`; README pressupõe uv no PATH.

### Entregas

- Catálogo com yolo11n-coco, arquivo/URL/release/SHA-256, termos e 80 classes.
- Extra detector com wheels CPU oficiais; importações pesadas só na implementação.
- Adapter YOLO, validação de checkpoint/classes/dispositivo, letterbox explícito,
  restauração de boxes, warm-up e tempos separados. Inferência offline.
- Renderer BGR com boxes/scores, sem mutar o frame original ou remover detecções fracas.
- Pipeline CLI compartilhado, detections.csv, timings.csv e manifest inicial/final.
- Script de smoke explícito, inventário de modelos/termos e CI manual opt-in.

### Comandos e resultados

- `/tmp/traffic-uv/uv sync --locked --extra api --extra video --extra detector`: aprovado.
- `.venv/bin/ruff check vision backend scripts`: aprovado.
- `.venv/bin/ruff format --check vision backend scripts`: aprovado (39 arquivos).
- `.venv/bin/pytest -q`: **130 aprovados**, 3 testes reais explicitamente deselecionados.
- `.venv/bin/pytest -m detector -q`: **3 aprovados**, 130 deselecionados.
  Conexões de rede bloqueadas no fixture real; assets já preparados localmente.
- `/tmp/traffic-py314/bin/pytest -q`: **130 aprovados** em Python 3.14.8, sem
  instalar o extra detector nesse ambiente leve.
- Ambiente separado `/tmp/traffic-detector314`, preparado com
  `UV_PROJECT_ENVIRONMENT=/tmp/traffic-detector314 /tmp/traffic-uv/uv sync --locked --extra video --extra detector --extra api --python 3.14`:
  `/tmp/traffic-detector314/bin/pytest -m detector -q` — **3 aprovados** em CPU.
- `.venv/bin/traffic-video prepare-model yolo11n-coco --directory checkpoints`:
  checkpoint local verificado, 5.613.764 bytes, SHA-256
  `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`.
- `.venv/bin/python scripts/smoke_detector.py --checkpoint checkpoints/yolo11n.pt --output-dir artifacts/wave-2-cpu-smoke --download-example`:
  vídeo H.264 de quatro frames repetindo imagem oficial, inferência CPU 640;
  detectou bus/person e exportou 20 observações de boxes no total. Isso não
  representa 20 objetos distintos. Artefatos/proveniência/relatório preservados
  localmente em diretório ignorado pelo Git.
- `.venv/bin/traffic-video process artifacts/wave-2-cpu-smoke/source-fixture.mp4 --output-dir artifacts/wave-2-cli-smoke --video-id cli-yolo-baseline --model yolo11n-coco --checkpoint checkpoints/yolo11n.pt --classes person bus --confidence 0.1 --image-size 640 --device cpu`:
  fluxo CLI real aprovado; 4 frames e CSV/manifest/timings íntegros.
- `/tmp/traffic-uv/uv build`: wheel e sdist construídos.
- Wheel instalado em `/tmp/traffic-core-wave0`: catálogo/CLI models funcionam
  sem FastAPI, PyAV, OpenCV, Torch ou Ultralytics; capability de vídeo informa
  extra ausente em JSON/exit 2.
- Wheel instalado em `/tmp/traffic-detector314` substituindo o editable e
  executado de `/tmp`: CLI com checkpoint verificado gera saída em
  `/tmp/traffic-wave2-wheel-output`, comprovando recursos empacotados e inferência
  fora do checkout. Metadados Git podem ser desconhecidos nesse cenário.

### Revisão

Revisão sequencial Codex: contratos, filtros, NMS, unidade das coordenadas e
condições de reprodução. Testes determinísticos cobrem boxes conhecidas em
retrato/paisagem/quadrado e dimensões com arredondamento, clipping e padding;
classes, parâmetros e predições inválidos; saída vazia; checkpoint divergente;
publicação sem sobrescrita e preservação de partial de outro processo;
renderização imutável e manutenção de observações fracas; reconciliação de
CSV/manifest/config/timings; erro acionável quando falta extra detector.

Testes com pesos reais confirmam mapa completo do checkpoint, CPU, bounds
originais em retrato/paisagem, detecção positiva de bus e entrada vazia. O
backend continua sem carregar bibliotecas científicas no startup; o núcleo e
o catálogo não importam Torch/Ultralytics. A suíte leve comprova esse isolamento.

### Limitações e verificações não executadas

- Sem GPU disponível/validada; CUDA exige runtime compatível e validação específica.
  O lock de desenvolvimento seleciona CPU. Não houve treino ou fine-tuning.
- Sem ground truth ou benchmark de tráfego real nesta onda: a imagem de exemplo
  repetida comprova integração, não precisão, continuidade temporal ou qualidade
  de contagem. Datasets reais continuam pendentes de aquisição/auditoria.
- A publicação da release não forneceu digest: o SHA pinado foi calculado
  durante o download HTTPS oficial, sem alegar assinatura fornecida pelo autor.
- Termos Ultralytics e proveniência do exemplo foram consultados e registrados
  em docs/model-inventory.md; nenhuma LICENSE do monorepo foi imposta.
- Frontend sem alterações; seus checks não foram repetidos. Workflow remoto
  não executado; job manual de smoke disponibilizado sem downloads no CI leve.
- Estatísticas de forward excluem warm-up; end-to-end inclui carga e warm-up.
  Variabilidade entre execuções não foi apresentada como meta de FPS.

Conclusão: gate da Onda 2 atendido localmente com detector e exports reais.
Próxima ação: Onda 3, integrando ByteTrack e alinhando seus limiares ao detector,
sem eliminar detecções de baixa confiança na visualização.

Artefato final regenerado após completar os campos de proveniência:
`.venv/bin/python scripts/smoke_detector.py --checkpoint checkpoints/yolo11n.pt --output-dir artifacts/wave-2-verified-smoke --download-example`.
Manifest final com 80 classes e versão do pacote, vídeo/CSV/summary aprovados.
O exemplo continua sendo imagem repetida sem GT, não benchmark de tráfego.
