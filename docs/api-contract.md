# API — contrato da Onda 9

Estado: liveness da Onda 0 mais uploads, jobs e artefatos. A inferência não
roda dentro do processo HTTP. O worker é outro processo:
`python -m backend.app.worker`.

Erros de produto usam `{"error_code", "error"}`. Paginação usa `limit`
(1–100, padrão 20) e `offset`.

## Rotas

| Método | Rota | Sucesso |
| --- | --- | --- |
| GET | `/api/health` | 200, liveness |
| POST | `/api/videos` | 201, corpo binário e header `x-filename` |
| GET | `/api/videos/{video_id}` | 200, metadados |
| GET | `/api/models` | 200, catálogo sem carregar pesos |
| POST | `/api/jobs` | 202, `state=queued` |
| GET | `/api/jobs` | 200, `items` e `total` |
| GET | `/api/jobs/{job_id}` | 200, progresso |
| POST | `/api/jobs/{job_id}/cancel` | 200 |
| GET | `/api/jobs/{job_id}/summary` | 200 só se `completed` |
| GET | `/api/jobs/{job_id}/events` | 200, CSV de cruzamentos paginado |
| GET | `/api/jobs/{job_id}/tracks` | 200, CSV de tracks paginado |
| GET | `/api/jobs/{job_id}/artifacts/{name}` | 200, nome da lista permitida |
| GET | `/api/experiments` | 200, jobs `completed` |

`POST /api/jobs` aceita `video_id`, `detector_model_id`, `tracker_config_id` e
`render_annotated_video`. Reprocessar cria outro `job_id`.

## Estados

`queued → running → completed | failed | cancelled`.

Cancelar `queued` encerra na hora. Cancelar `running` grava o pedido e o
worker o atende no próximo frame. Um worker morto, com heartbeat mais velho
que `TRAFFIC_STALE_AFTER_SECONDS` (padrão 30), vira `failed` com
`worker_interrupted`. Não retoma o meio do vídeo.

## Arquivos e limites

SQLite em `TRAFFIC_DATA_DIR/traffic.sqlite` (padrão `data/`). Vídeos em
`videos/{id}/source.mp4`. Artefatos em `jobs/{id}/`.

Download só aceita um nome da lista interna. `..` e caminhos compostos não
resolvem arquivo. Upload acima de `TRAFFIC_MAX_UPLOAD_BYTES` (512 MiB) ou da
cota `TRAFFIC_QUOTA_BYTES` responde 413. Retenção
`TRAFFIC_RETENTION_SECONDS` apaga jobs terminados; não apaga `queued` nem
`running`.

Vídeo que o probe rejeita responde 422 e não fica registrado. Summary de job
não concluído responde 409. Falha de disco fica `failed`, não `completed`.

## CORS

Métodos GET e POST. Headers `Accept` e `Content-Type`. Origins continuam os
de `TRAFFIC_ALLOWED_ORIGINS`.
