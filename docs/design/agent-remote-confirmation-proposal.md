# Proposta experimental: confirmação entre serviços

Estado: experimento isolado, NÃO decisão arquitetural aprovada nem integração
ativa. Leituras: ADR-0001, architecture.md e F09/F10. Agenda é dona das reservas;
banco compartilhado não autoriza o agente a gravá-las diretamente.

## Escolha recomendada
Manter serviços por domínio. Usar outbox SQL no agente e inbox idempotente no
serviço de domínio. Não adicionar broker para a prova inicial. Um dispatcher
futuro pode tentar entrega síncrona e reconciliar pendências duráveis.

Alternativa mais simples: comando local SQL atômico no banco compartilhado. Isso
reduz infraestrutura, mas mudaria a responsabilidade de escrita aprovada em
ADR-0001. Não foi adotada nem aplicada ao produto.

## Diagrama didático
```text
AGENTE / banco A                    DOMÍNIO / banco B
aprovação
  BEGIN
  consumir pending
  gravar outbox(command_id,
    identidade,ação,args originais)
  COMMIT
       ── comando ───────────────→ reautorizar
                                    BEGIN
                                    inserir inbox(command_id UNIQUE, hash)
                                    executar efeito + salvar resultado
                                    COMMIT
       ←── resultado/ACK ────────
  marcar entregue

Se ACK se perder:
  outbox ainda pending
  reenviar MESMO command_id ─────→ inbox já existe + hash igual
       ←── resultado gravado ────  sem repetir efeito
```

## Código real para explorar
`confirmations/remote_probe.py` é simulador, não repository de agenda no agente.
- `enqueue_command`: porta LOCAL do ledger; confirmação e outbox no mesmo commit.
- `SyntheticDomainInbox.accept`: receipt e efeito SQL no mesmo commit do banco B.
  PK resolve duplicatas; mesmo ID com conteúdo diferente retorna409.
- `OutboxDeliveryProbe.deliver`: chamada ocorre fora da transação A. Só marca
  entregue quando ACK corresponde a command_id/hash. Não pressupõe que timeout
  significa ausência de efeito.

Teste de perda de ACK: banco B confirma efeito; transporte simulado lança
TimeoutError; outbox fica pending; reabertura/redelivery retorna receipt e mantém
apenas um efeito. Testes também cobrem envio repetido, concorrência com engines
independentes, payload divergente, autorização negada, ACK estranho e rollback.
Durante a prova, um savepoint SQLite anterior ao BEGIN efetivo revelou receipt
persistido cedo. Foi removido: o código agora faz rollback integral antes de
consultar receipt commitado. O teste de falha protege essa decisão.

## O que foi comprovado, e o que não foi
Dois arquivos SQLite temporários, transporte por callable, efeitos fictícios.
Nenhuma rede, Gemini, rota, migração, worker ativo ou gravação em agenda/visitas.
Não chamar isto de exactly-once universal: a entrega é repetível; o efeito SQL
local é deduplicado pelo receipt durável no cenário testado.

Faltam PostgreSQL, crash real, failover, autenticação HTTP entre serviços,
validação schemas, política de retries/backoff/limite, telemetria e retenção dos
receipts. O hash identifica conteúdo; NÃO autentica remetente. authorizer real
deve validar identidade/vínculo e impedir ação fora do escopo. Portas não podem
realizar efeitos externos não transacionais. Dispatcher de produção não pode
tratar erros permanentes de autorização como retries infinitos.

## Decisão pendente antes de integrar
F10 exige200 com resposta/pendências e409 para confirmação já consumida. Enfileirar
não significa concluir reserva. Não modificar para202 sem decisão explícita.
Recomendação:200 apenas com resultado conhecido; falha/timeout não pode gerar
resposta de sucesso. Reconciliar internamente pelo command_id. O protocolo exato
para comunicar resultado incerto, retomar ADK e consultar resultado ainda precisa
ser definido e testado. **Um503, sozinho, não torna retry seguro**, e repetir a
confirmação externa deve continuar409 após consumo. Não foi implementada nenhuma
mudança nesse contrato. Lucas deve ver este tradeoff antes da integração real.

## Adversário: revogação depois do commit e antes do ACK
O efeito já ocorreu, o ACK se perdeu e o morador perdeu o vínculo. Reenviar pelo
caminho normal deve continuar negado: não liberar receipt/resultados a uma conta
revogada só porque ela era titular antes.

O experimento oferece `reconcile_receipt` separado, desativado por padrão.
Um authorizer de serviço obrigatório verifica principal técnico e escopo do
command_id. A consulta devolve SOMENTE ID, hash e committed, sem payload,
resultado, unidade, morador ou texto de conversa. O hash não é credencial.
Não existe rota HTTP ou segredo de serviço neste experimento.

```text
Domínio já commitou → ACK perdido → morador revogado
  caminho normal de comando/resultado → 403
  dispatcher autorizado → consulta receipt ID+hash
                          ← committed=true (sem detalhes)
  outbox pending → reconciled; result=NULL
  nenhuma reexecução; nenhum resultado entregue ao morador
```

`OutboxDeliveryProbe.reconcile` nunca chama send/effect. Receipt ausente mantém
pending e NÃO autoriza reenvio. Após reconciliação positiva, deliver só informa
estado interno reconciled/result_available=false. Esses objetos são de controle
interno, não o response público F10. Repetição da confirmação consumida continua
409 no ledger. O futuro endpoint de usuário ainda precisa reautorização atual
para qualquer leitura de estado, inclusive status; não expor dispatcher.

Provas adicionadas: commit+ACK perdido+revogação, reconciliação privilegiada,
nenhuma execução/reenviada (spies), resultado local omitido, moradores/serviços
não autorizados recusados, hash divergente409 e receipt ausente sem envio.
Suite total51 testes passou. A revogação não apaga o efeito já commitado nem
altera retrospectivamente sua validade; eventual cancelamento é outra ação.

Tradeoffs pendentes: identidade técnica real, escopo mínimo por serviço/tenant,
auditoria sem payload, retenção do receipt/hash, tratamento de erro permanente e
reconciliação operacional. Os argumentos originais continuam no outbox para
recuperação e exigem acesso restrito/retention; não há apagamento seguro de dados
nesta prova. O fluxo não concede ao usuário revogado acesso ao serviço técnico,
mas isso ainda precisa ser imposto no futuro transporte real.
