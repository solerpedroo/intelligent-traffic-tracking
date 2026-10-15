# Exemplos e fixtures

Vídeos de teste são gerados localmente por `scripts/generate_sample.py` e pela
suíte de testes, sem download. São formas geométricas originais, sem pessoas,
placas, dados de terceiros ou alegação de representar tráfego real.

Os conteúdos sintéticos gerados por esse script são disponibilizados sob
CC0-1.0. Isso não atribui licença aos datasets externos nem decide a licença
de todo o software. Arquivos grandes e artefatos gerados ficam fora do Git.

```bash
uv sync --locked --extra api --extra video
uv run --locked --extra api --extra video python scripts/generate_sample.py data/sample.mp4
uv run --locked --extra api --extra video python scripts/generate_sample.py data/sample-vfr.mp4 --profile vfr
uv run --locked --extra api --extra video traffic-video process data/sample-vfr.mp4 --output-dir artifacts/sample-vfr
```

Para dados reais e protocolos futuros, consultar [datasets](../docs/datasets.md).
