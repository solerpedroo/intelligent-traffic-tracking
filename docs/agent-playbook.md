# Protocolo de desenvolvimento

Entrada comum: [AGENTS.md](../AGENTS.md). Gates de produto:
[implementation-plan.md](implementation-plan.md).

## Ciclo por tarefa

1. **Planejar:** conferir onda/dependências, requisito do escopo, contratos e
   arquivos permitidos. Dividir a tarefa se não houver uma entrega verificável.
2. **Assumir:** preencher responsável e estado no cartão e workboard antes de
   editar código. Sessões Cursor/Codex compartilham essa posse.
3. **Implementar:** usar o mesmo núcleo na CLI e worker; manter o diff no limite
   declarado. Descobertas transversais exigem ADR e ajuste do cartão.
4. **Validar:** executar comandos reais; distinguir teste determinístico,
   integração com modelos/dados e inspeção manual. Anotar falhas e testes pulados.
5. **Revisar:** confrontar diff, requisito, contratos, evidências e validade das
   métricas. O mesmo agente pode fazer essa revisão em uma etapa separada.
6. **Concluir:** atualizar checklist, evidências e workboard. Deixar handoff se
   houver continuação que não seja óbvia a partir do cartão.

## Evidência mínima

Código alterado e razão, comandos e resultados, ambiente relevante, fixtures
usadas, limitações e decisão de revisão. Em experimentos: manifest, hashes de
dados/GT/checkpoint e localização de artefatos/relatórios. Nunca registrar
segredos, vídeos de terceiros ou grandes logs nos cartões.

## Cursor e Codex

`AGENTS.md` concentra as invariantes; `.cursor/rules/` fornece especializações.
Ambos leem os mesmos cartões e ADRs. Regras não dependem de memória, persona ou
um histórico de chat específico. Não duplicar defaults científicos em prompts.

Não editar os mesmos arquivos em sessões simultâneas. Contratos, catálogo,
migrações, cliente tipado e integração final precisam de uma posse por vez.
Antes de retomar, conferir `git status`, diff e handoff; preservar trabalho prévio.

## Encerramento de onda

- Todos os cartões necessários estão `done`, com evidência.
- Critérios da onda no plano cumpridos, inclusive integração real quando exigida.
- Docs e ADRs refletem o comportamento implementado.
- Workboard atualizado; não manter uma segunda lista de progresso neste arquivo.
- Nenhum resultado inventado ou teste pulado apresentado como aprovação.

Ao encontrar bloqueio externo, registrar o motivo e a próxima ação concreta.
Não fechar a onda com `not_evaluated` quando a avaliação é requisito da entrega.
