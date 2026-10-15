# Layout dos resultados de uma execução

Estes arquivos não são versionados. A CLI cria um diretório novo e só promove
cada artefato depois de fechá-lo. Arquivos `.partial` não são resultado válido.

Schema de exportação `1.0`. Unidades e ordem das colunas estão em
`vision/pipeline/schemas.py`.

| Artefato | Quando existe | Conteúdo |
| --- | --- | --- |
| `config.json` | sempre, antes do processamento | configuração resolvida, limites, política de tempo, SHA-256 da entrada |
| `manifest.json` | sempre | run, Git, software, detector/tracker quando selecionados |
| `summary.json` | só em sucesso do núcleo | totais reconciliáveis com os CSV e estado do MP4 |
| `failure.json` | falha ou cancelamento do núcleo | sem summary de sucesso |
| `frames.csv` | sucesso | índice original e tempo da mídia |
| `detections.csv`, `timings.csv` | com detector | boxes em pixels originais; tempos em milissegundos |
| `tracks.csv`, `trajectories.csv`, `track-lifetimes.csv` | com tracker | estados, centros e encerramento |
| `crossing_events.csv`, `crossing_windows.csv` | com linhas | eventos e janelas; vazio significa zero eventos |
| `zone_events.csv`, `zone_visits.csv`, `zone_occupancy.csv` | com ROI | visitas censuradas e ocupação observada |
| `heatmap_index.csv`, `heatmaps/*.npz` | com heatmap | contagens por célula; PNG é só preview |
| `video.mp4` | só se o encode anotado terminar | H.264, sem áudio, origem no primeiro frame selecionado |
| `preview.png` | se a codificação do primeiro frame funcionar | frame original, sem overlay |

`--no-annotated-video` omite `video.mp4` e marca o summary com aviso. Falha de
codec ou de preview faz o mesmo para o arquivo visual e mantém os números.
