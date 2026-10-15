# API — contrato da Onda 0

Estado: implementado apenas liveness. O [escopo §7](project-scope.md) descreve
rotas futuras; não é a lista de endpoints atualmente disponíveis.

## `GET /api/health`

Sem parâmetros ou corpo. Resposta HTTP 200, `application/json`:

```json
{
  "status": "ok",
  "service": "intelligent-traffic-tracking-api",
  "api_version": "v1"
}
```

Indica que o processo HTTP responde. Não testa modelo, checkpoint, worker,
storage, banco ou GPU. Não carrega `vision`, NumPy, OpenCV ou PyTorch.

Schema de resposta é explícito em `backend/app/schemas/health.py`. O cliente
TypeScript valida os três campos e rejeita resposta HTTP malsucedida, payload
incompatível ou erro de rede. Timeout de cinco segundos; indisponibilidade é
exibida no shell sem impedir a renderização do restante da página.

## Endpoints auxiliares

- `GET /openapi.json`: schema OpenAPI gerado pelo FastAPI.
- `GET /docs`: Swagger UI para inspeção manual.
- `GET /redoc`: visualização alternativa do schema.

As páginas de documentação padrão podem carregar assets externos. Health,
OpenAPI e a aplicação não dependem desses assets. Rotas de produto ainda não
implementadas, como `POST /api/jobs`, respondem 404.

## CORS e ambiente

Origins padrão: `http://localhost:3000` e `http://127.0.0.1:3000`.
Somente método GET e header Accept são permitidos na fundação; sem credentials.
Origins adicionais vêm de `TRAFFIC_ALLOWED_ORIGINS` (array JSON). Schemes
HTTP(S), host e porta são aceitos; paths, credenciais, query e fragmentos não.
Origins não permitidos não recebem `Access-Control-Allow-Origin`.

Variáveis inválidas impedem a criação da aplicação, em vez de corrigir valores
silenciosamente. O cliente usa `NEXT_PUBLIC_API_URL`, com fallback local em
`http://127.0.0.1:8000`. A API não chama o frontend.

## Evolução

Na Onda 9 entram uploads/jobs, paginação, progresso, cancelamento e artefatos.
Definir schemas, erros e versionamento antes de introduzir essas rotas. O
`schema_version` dos contratos científicos é independente de `api_version`.
