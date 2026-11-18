---
spec_template: 1
feature: F04
ceremony: full
prd_source: docs/prd/functional/F04-usuarios.md
---

# F04 — Gestão de usuários e perfis

## 1. Visão técnica

O serviço `users` mantém dados de contas em identidade e usa `auth` para validar o operador. O painel permite editar os campos autorizados, desativar e reativar contas. Desativação preserva o identificador usado pelo histórico.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F04](../../prd/functional/F04-usuarios.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../design/architecture.md). Este documento especifica os contratos da base e das etapas da integração identificadas na matriz.



O recorte de entrega vigente está no [PRD](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento). Casos identificados como integração do agente ou modo acadêmico permanecem especificados para a próxima etapa; não são condição de fechamento da administração manual. Sua ausência não significa aceite desses comportamentos.

## 2. Impacto arquitetural

CRUD de contas passa pelo proxy e chega a `users`. A API resolve a identidade e exige o papel administrativo antes de persistir em `identity-db`. O cadastro de apartamentos usa somente a projeção pública para confirmar que a conta é elegível.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0002](../../adr/ADR-0002-orm-e-integridade-transacional.md), [ADR-0003](../../adr/ADR-0003-identidade-central-e-autorizacao-por-recurso.md).

Manter contas desativadas para preservar vínculos. Usuários `admin` gerenciam perfis `admin` e `resident`. O papel é escolhido no cadastro e fica fixo, preservando a elegibilidade do responsável pelo apartamento. A criação usa email normalizado e único, com rollback na criação concorrente da mesma chave. Alterações de estado preservam pelo menos uma conta administrativa ativa. Mudar senha ou estado revoga as sessões da conta afetada. A migração converte papéis administrativos legados preservando os IDs e credenciais.

## 4. Visão de componentes

| Camada | Arquivo | Responsabilidade |
| --- | --- | --- |
| Router | services/users/routers/account_router.py | Receber DTO e identidade e chamar o controller |
| Controller | services/users/controllers/account_controller.py | Coordenar validação, persistência e serialização |
| Validator | services/users/validators/account_validator.py | Verificar permissão e regras da operação |
| Repository | services/users/repositories/account_repository.py | Consultar e escrever com SQLAlchemy em transação |
| Serializer | services/users/serializers/account_serializer.py | Produzir DTO público sem campos internos |
| Composição | services/users/main.py | Montar routers, middleware, Swagger e health do toolkit |

As schemas Pydantic validam tipo e formato. Validators não gravam e controllers não acessam Session ou engine. O repository aplica flush, locks e constraints conforme a operação. Falha faz rollback. A documentação OpenAPI declara os contratos de entrada, saída, erros e autenticação.

## 5. Contratos de interface

GET e POST em `/api/admin/users`. O cadastro recebe `name`, `email`, `password` e `role`. PATCH `/api/admin/users/{id}` atualiza os campos permitidos, incluindo `active`. A senha nova tem entre 12 e 256 caracteres. GET por ID devolve a projeção permitida. A resposta expõe `id`, `name`, `email`, `role` e `active`. O perfil do usuário corrente vem de `/api/auth/me`.

Email duplicado causa conflito. Campo inválido retorna mensagem por campo. Elevação indevida de papel retorna 403 e deixa a conta original intacta. Conta desativada perde acesso validado.

Entradas de identidade com caractere nulo são recusadas com 422 antes do repository. Email e nome seguem sua normalização explícita; a senha conserva espaços e conteúdo sem normalização implícita. Os testes de regressão estão em services/authentication/tests/test_identity_inputs.py e nas chamadas HTTP com dados sintéticos.

## 6. Modelo de dados

A conta contém um identificador estável, chave de email única, nome, papel, estado ativo e segredo derivado da senha. A alteração de status é uma atualização do perfil. A fronteira pública exclui o segredo derivado e os registros internos de sessões.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F04-AC01 | Base. Criar a conta pelo painel, autenticar, confirmar formato público e vincular unidade. | O cadastro devolve perfil público, aceita login da nova conta e permite vinculá-la. |
| F04-AC02 | Base. Em ambiente isolado, desativar as outras contas administrativas e tentar desativar a última. | A operação é recusada e uma conta administrativa continua ativa. |
| F04-AC03 | Base. Pedir lista administrativa e perfil próprio e inspecionar apenas a identidade autenticada. | A resposta não inclui registros alheios. |
| F04-AC04 | Base. Atualizar uma conta criada para o teste, repetir email em segunda conta, desativar e reapresentar token. | Edição persiste e a desativação invalida o acesso; duplicidade é rejeitada. |
| F04-SEC01 | Base. Inspecionar respostas válidas e de erro com credenciais descartáveis. | O JSON e a evidência não incluem senha ou hash. |
| NFR01-AC01 | Base. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. | A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. |
| NFR03-AC01 | Base. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas. | A evidência não inclui segredos ou objetos de unidades fora da autorização. |
