# Ledger de confirmações: aprender antes de conectar escritas

## Requisito e recorte
Leitura prévia: F09 spec/plan (SI09.3, pendência durável com item original,
retomada, recusa e replay) e F10 spec (404 sessão ausente; 409 pendência
inexistente, consumida ou de outra sessão). O experimento ADK mostrou que
repetir uma confirmação repete a tool: o domínio precisa proteger o efeito.

Esta fatia implementa `confirmations/ledger.py` com metadata separada. NÃO há
migração/bootstrap do produto, rota de confirmação, reserva/visita real, ADK
resume ou Gemini ligado. Banco e efeitos dos testes são exclusivamente sintéticos.

## Fluxo
```text
Criar intenção autorizada
  → copiar ação + argumentos originais
  → persistir pending (sessão, morador, unidade)
  → retornar ID opaco

Decisão externa (ID, booleano)
  → BEGIN
  → revalidar sessão / identidade / vínculo atual
  → UPDATE ... WHERE ID + sessão + morador + unidade + status=pending
      0 linhas → ROLLBACK → 409 (nenhum efeito)
      1 linha  → recusa: registrar rejected, sem efeito
               → aprovação: porta SQL local usa argumentos persistidos
  → gravar resultado e COMMIT juntos
      exceção → ROLLBACK consumo + efeito
```

## Três trechos para estudar
1. `create`: deepcopy evita que uma mudança posterior do caller altere o item
   aprovado. O registro conserva unidade e morador, não só sessão.
2. `decide`: UPDATE condicional é compare-and-set no banco. Dois processos não
   ganham o mesmo pending; o perdedor tem rowcount=0 e recebe409. Lock Python
   não participa dessa garantia.
3. `session.begin`: consumo e efeito SQL local pertencem à mesma transação.
   Falha depois do INSERT sintético reverte ambos e mantém pending. Nunca fazer
   commit dentro da porta de efeito.

A decisão não recebe novos argumentos da ação: apenas ID e booleano. Os detalhes
vêm da pendência original. Action deve existir no registro de portas confiáveis.
A aprovação é uma decisão do usuário, não garantia de disponibilidade futura:
a futura porta de reserva ainda precisa resolver a exclusividade no banco e
pode registrar resultado de indisponibilidade, conforme o contrato F10.

## Evidência desta fatia
Suite total41 testes aprovados, sete do ledger. Inclui aprovação/replay, recusa,
payload original, rollback conjunto após falha, reabertura de engine, autorização,
ID inválido, tipos e concorrência com dois processos Python spawn independentes
sobre o mesmo arquivo SQLite: um approved, outro409, uma linha de efeito.

## Limites e próximo marco
- `authorizer` é porta obrigatória, injetada. Nos testes consulta binding sintético.
  Ainda precisa adapter real que revalide identidade e bloqueie vínculo/sessão
  conforme regras do domínio; não basta reaproveitar autorização antiga.
- Não há FK para sessão de produção porque não se migrou schema. A composição
  real exige migração/constraints e revisão das regras de exclusão/retenção.
- A atomicidade vale para SQL na MESMA sessão/transação. Chamar serviço HTTP,
  Gemini ou outro banco dentro de effects quebra essa garantia. A arquitetura
  por serviços exigirá outbox + idempotency key no domínio, ou comando local
  transacional deliberadamente definido. Não ligar escritas antes dessa decisão.
- Ainda falta PostgreSQL, crash de processo no meio da transação, concorrência
  de alteração do vínculo, aprovação/recusa simultâneas, criação idempotente da
  mesma intenção e integração com eventos/retomada do ADK.
- Sessões ausentes/revogadas são recusadas pelo authorizer antes do ledger; não
  revelar dados de outra sessão. Nenhum endpoint novo foi publicado.

Pergunta de aprendizagem: por que salvar `approved` em uma transação e chamar
HTTP depois não garante uma única reserva? Porque uma queda entre essas etapas
pode perder o efeito, enquanto uma repetição pode duplicá-lo. O próximo marco
deve resolver essa fronteira, não esconder o problema com retry automático.
