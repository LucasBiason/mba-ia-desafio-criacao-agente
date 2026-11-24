---
status: accepted
date: 2026-11-23
decision-makers: [Responsável pelo produto]
source: ../design/architecture.md
source_section: "4. Fluxos de requisições e dados"
feature: F09
spec: ../specs/F09-chat-agente/spec.md
spec_section: "5. Contratos de interface"
---

# ADR-0009: Vincular delegação tipada a executores e recibos do servidor

## Contexto e problema

O portal precisa interpretar pedidos de reserva, visita e regulamento mantendo identidade, regras, confirmação e efeitos sob autoridade do servidor. Histórico contínuo pode conter respostas antigas incompatíveis com uma intenção atual; prosa do modelo não comprova permissão nem execução. A decisão e seus limites estão no [protocolo de F09](../specs/F09-chat-agente/spec.md#protocolo-interno-de-delegação), com efeitos em [F07](../specs/F07-reservas/spec.md) e [F08](../specs/F08-visitantes/spec.md).

## Fatores da decisão

- Preservar três agentes ADK, sessão existente e contratos públicos.
- Exigir confirmação externa para reserva paga e visita, com consumo único durável.
- Limitar o modelo à interpretação; validar operação, vínculo e dados no servidor.
- Reutilizar o ledger existente e impedir efeitos repetidos sem DDL no HTTP.

## Opções consideradas

- Delegação tipada validada no servidor, destino calculado e uma ferramenta executora por especialista.
- Escolha livre de transferência e de ferramentas pelos modelos, com resposta final em prosa livre.

## Resultado da decisão

Usamos delegação tipada com validação explícita e mapa fixo para reservas e convivência. O principal extrai o pedido atual; cada especialista executa somente o envelope imutável vinculado ao turno. Não existe argumento de identidade ou aprovação emitido pelo modelo. A API pública ADK de transferência mantém o handoff entre os três agentes; configurações de chamada obrigatória complementam as guardas do servidor.

O resultado do domínio e do ledger gera a resposta canônica. Dados incompletos não produzem efeito; uma violação de protocolo produz indisponibilidade identificável. Uma execução já confirmada conserva o recibo mesmo diante de falha posterior de geração. A confirmação humana permanece exclusivamente na rota existente, com argumentos recuperados da pendência original.

A proposta usa chave estável gerada no servidor e a PK existente do ledger. Repetir a mesma operação no turno conserva a pendência original; conteúdo divergente conflita. Não há armazenamento adicional nem migração implícita. Transações de domínio não abrangem chamadas ao modelo. A API do assistente do avaliador conserva seu próprio protocolo.

### Consequências

- Positiva: identidade, destino, confirmação e recibo passam por fronteiras verificáveis; o modelo não inventa um efeito confirmado.
- Negativa: o servidor mantém schemas, despacho e serialização canônica para cada operação; o segundo agente continua dependente da disponibilidade do provedor.
- Neutra: o transcript anterior permanece intacto, enquanto o contexto de interpretação usa o pedido atual e fatos canônicos autorizados.

### Confirmação

Verificar o Runner real com modelo controlado: validação de schema, handoff, rejeição de transferência direta, envelope alheio e execução repetida. Com provedor real e dados sintéticos isolados, exigir pendência de visita em conversa existente, zero autorização antes da decisão e reserva paga subsequente conforme o novo pedido. Conferir recusa, aprovação, replay 409, reinício, histórico público filtrado e exclusividade concorrente.
