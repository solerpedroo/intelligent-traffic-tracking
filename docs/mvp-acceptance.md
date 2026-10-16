# Aceitação do MVP — Onda 12

Estado: fechado em 2026-10-16 com o teste local do navegador. O vídeo
anotado ficou em `data/`, que não entra no git. Não há arquivo `LICENSE`.

## Regressão desta sessão

Em 2026-10-16, no checkout local:

- `.venv/bin/ruff check vision backend scripts` aprovado.
- `.venv/bin/pytest -q`, rodando ao mesmo tempo que o frontend: **265
  aprovados, 1 falha**. A falha foi
  `test_parallel_connections_migrate_once` com `database is locked`.
- O mesmo teste, sozinho em seguida: **1 aprovado**.
- O timeout do SQLite passou de 5 s para 30 s depois dessa falha. A suíte
  completa, repetida em seguida, ficou em **266 aprovados**, 17 deselecionados.
- `frontend`: `npm run lint`, `npm run test` (**25**) e `npm run typecheck`
  aprovados. Playwright e `npm run build` não foram repetidos nesta sessão.
- Ensaio local no navegador, vídeo `Sysvideo-4K-8-SnapYT.App (1).mp4`,
  1920×1080, 47,68 s, 1192 frames. Job
  `777c59836493467fb9912988b1e147a7` terminou `completed`. CPU, YOLO11n e
  ByteTrack. `elapsed_s` 80,42, inferência 29,25 forwards/s, ponta a ponta
  14,82 frames/s. O MP4 anotado foi publicado e o navegador o leu com
  status 206. Disco: 16 MB do vídeo e 58 MB do job. RSS não foi amostrado.
  Esse job não tinha linhas de contagem. O arquivo-fonte não foi versionado.

## Critérios do escopo §14

| Critério | Evidência | Estado |
| --- | --- | --- |
| Importar vídeo e ver metadados | CLI `probe` e `POST /api/videos`; testes de jobs | implementado |
| YOLO detecta classes selecionadas | Onda 2 e smoke com `checkpoints/yolo11n.pt`; baseline MOT15 em `docs/evaluation.md` | implementado |
| IDs e trajetórias | Onda 3; `tracks.csv` e `trajectories.csv` | implementado |
| Desenhar linhas e sentidos | Onda 4 e workspace da Onda 10 | implementado |
| Contar por classe e sentido | `crossing_events.csv` e summary `by_line_class_direction` | implementado |
| Jitter não duplica | testes sintéticos da Onda 4 | implementado |
| ROI e ocupação | Ondas 5 e 11; `zone_occupancy.csv` | implementado |
| Vídeo e CSV/JSON | Onda 6; falha de MP4 não apaga os números | implementado |
| Dashboard | `/analytics`: contagens, janelas e FPS, com `not_evaluated` explícito | implementado |
| Jobs sem bloquear o HTTP | 202, worker separado, erro visível no viewer | implementado |
| Testes críticos | suítes Python e Vitest acima | implementado; a corrida do SQLite falhou uma vez sob carga |
| MOT só com GT | Onda 7; a UI não mostra ID switch sem referência | implementado |
| Três experimentos | `experiments/reports/wave8-summary.json` | implementado |
| README de instalação e limites | [README.md](../README.md) | texto atualizado; vídeo de portfólio ausente |

## Limites deste fechamento

- A demonstração é o MP4 do job acima, em `data/`. Não foi copiada para o
  repositório: o nome do arquivo indica download de terceiro.
- Não existe `LICENSE`. Os pesos YOLO11n estão sob AGPL-3.0 ou Enterprise, e
  o MOT15 sob CC BY-NC-SA 3.0. A revisão não escolhe a licença do código.
- Não houve clone limpo novo. RSS não foi medido.
- Screenshots de pessoas ou placas não foram adicionados.
