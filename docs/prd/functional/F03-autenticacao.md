# F03 — Autenticação e autorização

Domínio: Segurança | Onda: 2 | Prioridade: 1

Conforms to: NFR01, NFR03

## Situação na primeira entrega

**Implementada com verificações residuais.** O recorte implementado é login, JWT, autorização, saída e recusa em indisponibilidade. Código de referência em `services/identity/app.py` e `services/common.py` e `web/src/app.jsx`. Evidência disponível em [validação](../../validacao.md) e [pacote de entrega](../../entrega-01.md). A tabela abaixo registra o alcance de cada critério.

| Critério | Situação documental |
| --- | --- |
| F03-AC01 | Implementação presente; evidência e aceite vinculados ao contrato |
| F03-AC02 | Implementação presente; evidência e aceite vinculados ao contrato |
| F03-AC03 | Implementação presente; evidência e aceite vinculados ao contrato |
| F03-AC04 | Conferir prova específica de expiração ou resposta de entrada no contrato |
| F03-SEC01 | Implementação presente; evidência e aceite vinculados ao contrato |
| F03-SEC02 | Implementação presente; evidência e aceite vinculados ao contrato |

## Descrição

Emitir uma sessão autenticada e validar identidade e permissão antes de operações privadas, incluindo bloqueio quando a identidade estiver indisponível.

Como usuário do residencial, quero entrar com minhas credenciais e ter acesso às operações do meu papel, Administração ou Morador.

A referência de produto original é FR03. A correspondência dos critérios anteriores é F03-AC01 ↔ FR03/AC01, F03-AC02 ↔ FR03/AC02, F03-AC03 ↔ FR03/AC03, F03-AC04 ↔ FR03/AC04. Critérios adicionais descrevem verificações específicas desta separação de etapas.

## Capacidades

- Consumes: F01.
- Provides: Login, usuário atual, logout, introspecção e contexto verificado de papel para serviços consumidores.
- Integração: O navegador se autentica pelo proxy. `users` e `condo` reenviam o bearer ao serviço de autenticação por conexão interna e aplicam também as permissões específicas do recurso. JWT assinado e revogação ficam sob a mesma autoridade. Apenas a identidade deriva o papel confiável.

## Comportamento esperado

- **Dado** uma conta ativa com credenciais válidas
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** login devolve uma sessão JWT aceito na leitura privada apropriada ao papel.

- **Dado** uma rota privada acessada com token ausente, vencido, adulterado ou revogado
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** o acesso retorna 401 sem executar a operação.

- **Dado** um morador com sessão válida em rota administrativa
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** o acesso retorna 403 sem efetivar mutação.

- **Dado** a identidade centralizada indisponível em teste isolado
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** o consumidor devolve erro de dependência e não executa a ação.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F03-AC01 | Uma conta ativa com credenciais válidas | Login devolve uma sessão JWT aceito na leitura privada apropriada ao papel | Autenticar administrador e morador e consultar o perfil e a superfície privada permitida |
| F03-AC02 | Uma rota privada acessada com token ausente, vencido, adulterado ou revogado | O acesso retorna 401 sem executar a operação | Variar os quatro estados com massa efêmera, comparar as respostas e conferir a persistência |
| F03-AC03 | Um morador com sessão válida em rota administrativa | O acesso retorna 403 sem efetivar mutação | Enviar o mesmo POST como administrador e morador, comparar estados e status |
| F03-AC04 | A identidade centralizada indisponível em teste isolado | O consumidor devolve erro de dependência e não executa a ação | Induzir falha da introspecção, obter 503 e comparar o estado após reativar o serviço |

A etapa de cada prova está identificada na [spec desta funcionalidade](../../specs/F03-autenticacao/spec.md#7-estratégia-de-testes).

## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F03-SEC01 | Fronteiras e escopo | A sessão perde validade no servidor e o navegador retorna ao login | Fazer logout, retomar a rota privada e reapresentar o bearer anterior |
| F03-SEC02 | Fronteiras e escopo | A resposta recusa acesso sem confirmar a existência da conta ou revelar segredo | Comparar corpo e status dos erros e revisar o conteúdo do registro da aplicação |

## Fora do escopo

Cadastros públicos, autenticação multifator, login federado e exigência de JWT no futuro modo acadêmico local.

## Tratamento de erros

Credencial ou token inválido, expirado ou revogado retorna 401. Papel insuficiente retorna 403. Dependência indisponível retorna 503 na rota consumidora e não causa operação parcial.
