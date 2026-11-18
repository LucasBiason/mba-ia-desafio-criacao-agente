---
spec_template: 1
feature: F03
ceremony: full
prd_source: docs/prd/functional/F03-autenticacao.md
---

# F03 — Autenticação e autorização

## 1. Visão técnica

O serviço `auth` verifica a credencial e emite JWT HS256 de uma hora, associado a uma sessão revogável. Os serviços consumidores consultam a identidade centralizada. A interface associa o token à sessão do navegador e limpa o contexto ao sair ou quando a sessão se torna inválida.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F03](../../prd/functional/F03-autenticacao.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../design/architecture.md). Este documento especifica os contratos da base e das etapas da integração identificadas na matriz.



O recorte de entrega vigente está no [PRD](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento). Casos identificados como integração do agente ou modo acadêmico permanecem especificados para a próxima etapa; não são condição de fechamento da administração manual. Sua ausência não significa aceite desses comportamentos.

## 2. Impacto arquitetural

O navegador se autentica pelo proxy. Os serviços de usuários, apartamentos, áreas, agenda, visitas, configurações e agente reenviam o bearer ao serviço de autenticação por conexão interna e aplicam também as permissões específicas do recurso. JWT assinado e revogação ficam sob a mesma autoridade. Apenas a identidade deriva o papel confiável.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0003](../../adr/ADR-0003-identidade-central-e-autorizacao-por-recurso.md).

Aplicar papel `admin` ou `resident` no servidor, além de checar sessão vigente e conta ativa. Guardar hash Argon2id e referência de sessão no banco de identidade. Depois de oito tentativas consecutivas de login numa janela de quinze minutos, a próxima recebe 429. Um login válido limpa a contagem. A criação de sessão obtém lock de linha e reconfirma credencial e estado, protegendo alterações concorrentes. Os serviços dependentes falham fechados quando a introspecção fica indisponível.

## 4. Visão de componentes

| Camada | Arquivo | Responsabilidade |
| --- | --- | --- |
| Router | services/authentication/routers/authentication_router.py | Receber DTO e identidade e chamar o controller |
| Controller | services/authentication/controllers/authentication_controller.py | Coordenar validação, persistência e serialização |
| Validator | services/authentication/validators/authentication_validator.py | Verificar permissão e regras da operação |
| Repository | services/authentication/repositories/session_repository.py | Consultar e escrever com SQLAlchemy em transação |
| Serializer | services/authentication/serializers/authentication_serializer.py | Produzir DTO público sem campos internos |
| Composição | services/authentication/main.py | Montar routers, middleware, Swagger e health do toolkit |

As schemas Pydantic validam tipo e formato. Validators não gravam e controllers não acessam Session ou engine. O repository aplica flush, locks e constraints conforme a operação. Falha faz rollback. A documentação OpenAPI declara os contratos de entrada, saída, erros e autenticação.

## 5. Contratos de interface

POST `/api/auth/login` recebe `email` e `password`, retorna `access_token`, `token_type`, `expires_in` e `user`. GET `/api/auth/me` apresenta o perfil público. POST `/api/auth/logout` responde 204 e revoga a sessão corrente. Use `Authorization: Bearer` nas APIs privadas. GET `/internal/identity` exige autorização serviço a serviço além do bearer e fica fora do proxy público.

Credencial ou token inválido, expirado ou revogado retorna 401. Papel insuficiente retorna 403. Dependência indisponível retorna 503 na rota consumidora e não causa operação parcial.

Entradas de identidade com caractere nulo são recusadas com 422 antes do repository. Email e nome seguem sua normalização explícita; a senha conserva espaços e conteúdo sem normalização implícita. Os testes de regressão estão em services/authentication/tests/test_identity_inputs.py e nas chamadas HTTP com dados sintéticos.

## 6. Modelo de dados

Conta persistida com hash de senha e estado ativo. Cada sessão tem identificador e validade e é verificável no banco de identidade. As operações de login e logout são associadas a uma única sessão. Logs e respostas excluem senhas, chave de assinatura e token integral.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F03-AC01 | Base. Autenticar administrador e morador e consultar o perfil e a superfície privada permitida. | Login devolve uma sessão JWT aceito na leitura privada apropriada ao papel. |
| F03-AC02 | Base. Variar os quatro estados com massa efêmera, comparar as respostas e conferir a persistência. | O acesso retorna 401 sem executar a operação. |
| F03-AC03 | Base. Enviar o mesmo POST como administrador e morador, comparar estados e status. | O acesso retorna 403 sem efetivar mutação. |
| F03-AC04 | Base. Induzir falha da introspecção, obter 503 e comparar o estado após reativar o serviço. | O consumidor devolve erro de dependência e não executa a ação. |
| F03-SEC01 | Base. Fazer logout, retomar a rota privada e reapresentar o bearer anterior. | A sessão perde validade no servidor e o navegador retorna ao login. |
| F03-SEC02 | Base. Comparar corpo e status dos erros e revisar o conteúdo do registro da aplicação. | A resposta recusa acesso sem confirmar a existência da conta ou revelar segredo. |
| NFR01-AC01 | Base. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. | A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. |
| NFR03-AC01 | Base. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas. | A evidência não inclui segredos ou objetos de unidades fora da autorização. |
