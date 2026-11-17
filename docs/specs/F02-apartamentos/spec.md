---
spec_template: 1
feature: F02
ceremony: full
prd_source: docs/prd/functional/F02-apartamentos.md
---

# F02 — Cadastro de apartamentos

## 1. Visão técnica

O serviço `condo` mantém as unidades e recebe um identificador público de morador. Cada apartamento tem no máximo um usuário do tipo `resident`, que representa o proprietário e responsável. Um morador pode responder por mais de uma unidade. Outros ocupantes ficam fora do modelo. A identidade obtida pelo backend valida o perfil; cada sessão seleciona um único apartamento autorizado.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F02](../../prd/functional/F02-apartamentos.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../arquitetura.md). Este documento especifica os contratos da base e das etapas da aula identificadas na matriz.

## 2. Impacto arquitetural

Cadastro passa pelo proxy e pelo guard de identidade do serviço de condomínio. A verificação de conta elegível consulta `users` por fronteira interna. Reservas, visitantes e futuros pedidos de agente se referem à unidade registrada no próprio domínio.

## 3. Decisões técnicas

O número é único e normalizado em maiúsculas, com até dez dígitos e uma letra opcional. A unidade tem um código interno persistente, `id`, que permanece ao editar o número. A edição troca o número enquanto a unidade estiver sem histórico. Referências impedem alteração da chave usada por reservas, visitas ou sessões. O vínculo é opcional e aceita usuário do tipo Morador em novas associações. Colisões e violações de dependência cancelam a escrita por rollback.

## 4. Visão de componentes

- Tela administrativa consulta a tabela, cadastra unidades e gerencia o vínculo com uma conta.
- Tela de morador consulta suas unidades e permite mudar a unidade ativa para novas operações.
- Serviço de condomínio valida papel, número, conta e dependências antes de persistir.

## 5. Contratos de interface

GET e POST em `/api/admin/apartments`. O cadastro recebe `number` e `resident_id` opcional. PATCH e DELETE em `/api/admin/apartments/{number}` fazem edição do número ou vínculo e exclusão sujeita à integridade. GET no mesmo caminho devolve o cadastro para a administração. GET em `/api/resident/apartments` devolve somente unidades da conta autenticada. A projeção administrativa fornece `id`, `number` e `resident_id`. O campo `resident_id` projeta o vínculo para o painel mostrar o nome do usuário responsável.

Número repetido gera conflito. Conta inexistente ou com papel incompatível rejeita o vínculo. A ativação do login é gerenciada separadamente. A tentativa de excluir unidade referenciada preserva os registros dependentes e informa o motivo. A falha da identidade não autoriza a mutação.

## 6. Modelo de dados

A tabela `apartments` guarda `id` e `number`. A relação `apartment_residents` usa o código da unidade para apontar a um usuário morador. A importação inicial usa número e nome de `apartamentos.json` para preencher unidade, usuário e relação. A atualização dos volumes anteriores conserva vínculos explícitos e mantém a titularidade conhecida de reservas e visitas.

## 7. Estratégia de testes

O [contrato](contract.md) organiza as verificações por critério. Use credenciais locais e massa descartável. **Base** é o comportamento especificado para a aplicação preparada. **Aula do agente** e **Avaliação acadêmica** identificam os testes das etapas guiadas. O [registro de validação](../../validacao.md) indica quais verificações foram de fato executadas.

| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F02-AC01 | Base. Cadastrar uma unidade, editar uma segunda e consultar a API de unidades com credenciais do morador. | O painel associa duas unidades à mesma conta e ambas aparecem na lista própria do morador. |
| F02-AC02 | Base. Criar uma unidade, repetir POST com vínculo diferente e comparar o estado obtido por GET. | A tentativa duplicada retorna conflito e preserva a unidade original. |
| F02-AC03 | Base. Tentar criar e editar unidades como morador, em seguida comparar a lista administrativa. | As operações administrativas são recusadas sem persistir alterações. |
| F02-AC04 | Base. Tentar DELETE sobre unidade de fixture com dependência e consultar a unidade e a agenda. | A exclusão é bloqueada e o histórico fica disponível. |
| F02-AC05 | Base. Conferir usuários e apartamentos importados e consultar uma unidade de teste após renumerá-la. | A carga associa o usuário morador da fonte à unidade, e o código da unidade editada se mantém após alterar o número. |
| F02-SEC01 | Base. Comparar GET de unidades do morador a duas unidades administrativas. | A consulta pessoal não devolve unidades de outras contas. |
| NFR01-AC01 | Base. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. | A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. |
| NFR03-AC01 | Base. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas. | A evidência não inclui segredos ou objetos de unidades fora da autorização. |

### Situação da execução

Implementada; aceite de entrega pendente. Código e número de unidade, responsável único, histórico preservado. Fonte do código: `services/domain/app.py; web/src/admin.jsx`. As evidências disponíveis são tests/test_api.py — contas, apartamentos e importação. Esta revisão é retrospectiva e não atesta a ordem histórica de invocação das skills. Critérios de aula e avaliação continuam pendentes. A [entrega](../../entrega-01.md) concentra o fechamento.

Revisão das fontes: índice atualizado com F11–F14 conferido; IDs e dependências de domínio anteriores preservados.

Conferência final: comportamentos do requisito vinculados aos procedimentos de aceite e situação da primeira entrega.
