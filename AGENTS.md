# Intelligent Traffic Tracking — orientação para agentes

## Estado e início de sessão

Projeto em planejamento. Nenhuma onda de software concluída. Consulte o estado
atual em [docs/agentic/workboard.md](docs/agentic/workboard.md).

1. Leia [o escopo](docs/project-scope.md), [a análise](docs/scope-analysis.md)
   e [o plano](docs/implementation-plan.md).
2. Leia [as decisões](docs/agentic/architecture-decisions.md) e o cartão da
   tarefa ativa em `docs/agentic/tasks/`.
3. Antes de código, reivindique uma tarefa delimitada e confira dependências.
   Divida cartões grandes usando `docs/agentic/task-template.md`.
4. Leia as regras aplicáveis em `.cursor/rules/`, inclusive ao usar Codex.
5. Implemente, valide, registre evidências e atualize cartão/workboard.

## Postura de engenharia

Atue com rigor de engenharia sênior e de pesquisa em visão computacional:
contratos explícitos, decisões justificadas, testes relevantes e resultados
reproduzíveis. Não invente credenciais, benchmarks, resultados ou aprovações.
Documentação em português; código, API, CLI e interface em inglês.

## Arquitetura e invariantes

- `vision/`: núcleo Python reutilizável; nenhuma dependência de FastAPI/React.
- `backend/`: HTTP, storage e ciclo de jobs; worker em processo separado.
- `frontend/`: configuração, visualização e análise dos resultados do núcleo.
- CLI e worker usam o mesmo pipeline. CPU deve funcionar; GPU é opcional.
- Câmera fixa, um vídeo por execução, um job ativo por worker no MVP.
- Boxes em pixels originais; geometrias persistidas normalizadas; timestamps
  da mídia original. Política VFR/fallback explícita.
- Tracker/contador/ROI resetados por execução. Buffers recentes limitados;
  trajetórias completas persistidas em streaming.
- Contar interseções com segmentos finitos e histerese; deduplicar por
  execução/linha/ID/sentido. ID não representa identidade real ou persistente.
- Preservar detecções fracas necessárias ao ByteTrack. Registrar pesos/hash,
  class mapping, parâmetros resolvidos e ambiente no manifest.
- Métricas MOT e ID switches confirmados exigem GT apropriado; ausente não é zero.
- Não versionar vídeos/checkpoints sem permissão, nem resultados fictícios.
- Preservar resultados numéricos se apenas a renderização falhar; reportar aviso
  e estado do artefato. Falha do núcleo nunca equivale a job completo.

## Fonte de verdade e colaboração

Requisitos: escopo. Sequência e gates: plano. Decisões aceitas: ADRs.
Estado: workboard. Trabalho específico/evidência: cartão. Regras Cursor
especializam essas decisões, sem manter um segundo plano independente.
Conflito real entre documentos exige correção explícita, não escolha silenciosa.

Cursor e Codex usam este mesmo protocolo. Papéis de planejamento,
implementação, testes e revisão podem ser exercidos sequencialmente pelo mesmo
agente. Não é necessário instalar agentes customizados ou executar subagentes.
Se houver sessões simultâneas, definir posse e arquivos distintos e serializar
contratos, catálogo, migrações e integração; verificar alterações locais existentes.

Use `docs/agentic/handoff-template.md` apenas para trabalho interrompido,
bloqueado ou continuação não óbvia. Preserve o estado real do diff, inclusive
alterações não commitadas, e indique sua origem. Não assumir que contexto de chat
substitui documentação ou que trabalho não commitado não existe.

## Validação e encerramento

Ainda não há comandos de software executáveis. A Onda 0 os estabelecerá e os
registrará no README e no cartão; não alegar testes existentes nesta fase.
Depois disso, execute os checks exigidos pelo cartão e pela área alterada.
Testes pulados precisam de motivo; mocks não substituem integração real.
Feche uma onda apenas com critérios e evidências completos.

Não iniciar fine-tuning, outro tracker, RTSP, múltiplas câmeras, identificação
pessoal ou deploy em nuvem como consequência implícita de uma tarefa do MVP.
Próxima tarefa: [wave-0-foundation](docs/agentic/tasks/wave-0-foundation.md).
