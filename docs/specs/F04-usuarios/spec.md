---
spec_template: 1
feature: F04
ceremony: full
prd_source: docs/prd/functional/F04-usuarios.md
---

# F04 — Gestão de usuários e perfis

## 1. Visão técnica

O serviço `users` mantém dados de contas em identidade e usa `auth` para validar o operador. O painel permite editar os campos autorizados, desativar e reativar contas. Desativação preserva o identificador usado pelo histórico.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F04](../../prd/functional/F04-usuarios.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../arquitetura.md). Este documento especifica os contratos da base e das etapas da aula identificadas na matriz.

## 2. Impacto arquitetural

CRUD de contas passa pelo proxy e chega a `users`. A API resolve a identidade e exige o papel administrativo antes de persistir em `identity-db`. O cadastro de apartamentos usa somente a projeção pública para confirmar que a conta é elegível.

## 3. Decisões técnicas

Manter contas desativadas para preservar vínculos. Usuários `admin` gerenciam perfis `admin` e `resident`. O papel é escolhido no cadastro e fica fixo, preservando a elegibilidade do responsável pelo apartamento. A criação usa email normalizado e único, com rollback na criação concorrente da mesma chave. Alterações de estado preservam pelo menos uma conta administrativa ativa. Mudar senha ou estado revoga as sessões da conta afetada. A migração converte papéis administrativos legados preservando os IDs e credenciais.

## 4. Visão de componentes

- Formulário administrativo de criação e edição de contas.
- Serviço `users` valida papel, email, alterações permitidas e estado da conta.
- Banco de identidade serializa operações de cadastro concorrentes e retém o identificador público.

## 5. Contratos de interface

GET e POST em `/api/admin/users`. O cadastro recebe `name`, `email`, `password` e `role`. PATCH `/api/admin/users/{id}` atualiza os campos permitidos, incluindo `active`. A senha nova tem entre 12 e 256 caracteres. GET por ID devolve a projeção permitida. A resposta expõe `id`, `name`, `email`, `role` e `active`. O perfil do usuário corrente vem de `/api/auth/me`.

Email duplicado causa conflito. Campo inválido retorna mensagem por campo. Elevação indevida de papel retorna 403 e deixa a conta original intacta. Conta desativada perde acesso validado.

## 6. Modelo de dados

A conta contém um identificador estável, chave de email única, nome, papel, estado ativo e segredo derivado da senha. A alteração de status é uma atualização do perfil. A fronteira pública exclui o segredo derivado e os registros internos de sessões.

## 7. Estratégia de testes

O [contrato](contract.md) organiza as verificações por critério. Use credenciais locais e massa descartável. **Base** é o comportamento especificado para a aplicação preparada. **Aula do agente** e **Avaliação acadêmica** identificam os testes das etapas guiadas. O [registro de validação](../../validacao.md) indica quais verificações foram de fato executadas.

| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F04-AC01 | Base. Criar a conta pelo painel, autenticar, confirmar formato público e vincular unidade. | O cadastro devolve perfil público, aceita login da nova conta e permite vinculá-la. |
| F04-AC02 | Base. Em ambiente isolado, desativar as outras contas administrativas e tentar desativar a última. | A operação é recusada e uma conta administrativa continua ativa. |
| F04-AC03 | Base. Pedir lista administrativa e perfil próprio e inspecionar apenas a identidade autenticada. | A resposta não inclui registros alheios. |
| F04-AC04 | Base. Atualizar uma conta criada para o teste, repetir email em segunda conta, desativar e reapresentar token. | Edição persiste e a desativação invalida o acesso; duplicidade é rejeitada. |
| F04-SEC01 | Base. Inspecionar respostas válidas e de erro com credenciais descartáveis. | O JSON e a evidência não incluem senha ou hash. |
| NFR01-AC01 | Base. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. | A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. |
| NFR03-AC01 | Base. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas. | A evidência não inclui segredos ou objetos de unidades fora da autorização. |

### Situação da execução

Implementada; aceite de entrega pendente. Tipos Administração e Morador; cadastro, edição e ativação; proteção da última administração. Fonte do código: `services/identity/app.py; web/src/admin.jsx`. As evidências disponíveis são tests/test_api.py — contas e última administração. Esta revisão é retrospectiva e não atesta a ordem histórica de invocação das skills. Critérios de aula e avaliação continuam pendentes. A [entrega](../../entrega-01.md) concentra o fechamento.

Revisão das fontes: índice atualizado com F11–F14 conferido; IDs e dependências de domínio anteriores preservados.

Conferência final: comportamentos do requisito vinculados aos procedimentos de aceite e situação da primeira entrega.
