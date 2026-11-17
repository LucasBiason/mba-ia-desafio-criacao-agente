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

## 2. Impacto arquitetural

O navegador se autentica pelo proxy. `users` e `condo` reenviam o bearer ao serviço de autenticação por conexão interna e aplicam também as permissões específicas do recurso. JWT assinado e revogação ficam sob a mesma autoridade. Apenas a identidade deriva o papel confiável.

## 3. Decisões técnicas

Aplicar papel `admin` ou `resident` no servidor, além de checar sessão vigente e conta ativa. Guardar hash Argon2id e referência de sessão no banco de identidade. Depois de oito tentativas consecutivas de login numa janela de quinze minutos, a próxima recebe 429. Um login válido limpa a contagem. A criação de sessão obtém lock de linha e reconfirma credencial e estado, protegendo alterações concorrentes. Os serviços dependentes falham fechados quando a introspecção fica indisponível.

## 4. Visão de componentes

- Tela de login recebe email e senha e direciona para a área do perfil retornado.
- `auth` autentica, assina, revoga e resolve a identidade atual.
- Dependências de autenticação na API retornam erro de identidade ou indisponibilidade antes de executar ações.
- Roteamento do frontend reduz navegação indevida. A autorização efetiva é aplicada na API.

## 5. Contratos de interface

POST `/api/auth/login` recebe `email` e `password`, retorna `access_token`, `token_type`, `expires_in` e `user`. GET `/api/auth/me` apresenta o perfil público. POST `/api/auth/logout` responde 204 e revoga a sessão corrente. Use `Authorization: Bearer` nas APIs privadas. GET `/internal/identity` exige autorização serviço a serviço além do bearer e fica fora do proxy público.

Credencial ou token inválido, expirado ou revogado retorna 401. Papel insuficiente retorna 403. Dependência indisponível retorna 503 na rota consumidora e não causa operação parcial.

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
