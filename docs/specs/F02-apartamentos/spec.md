---
spec_template: 1
feature: F02
ceremony: full
prd_source: docs/prd/functional/F02-apartamentos.md
---

# F02 — Cadastro de apartamentos

## 1. Visão técnica

O serviço `apartments` mantém as unidades e recebe um identificador público de morador. Cada apartamento tem no máximo um usuário do tipo `resident`, que representa o proprietário e responsável. Um morador pode responder por mais de uma unidade. Outros ocupantes ficam fora do modelo. A identidade obtida pelo backend valida o perfil; cada sessão de chat fixa uma única unidade autorizada; as consultas do portal informam a unidade selecionada.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F02](../../prd/functional/F02-apartamentos.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../design/architecture.md). Este documento especifica os contratos da base e das etapas da integração identificadas na matriz.



O [recorte de entrega](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) separa base administrativa, portal com assistente e API do assistente. Os modos dos critérios mantêm a superfície exigida; implementar não equivale a demonstrar o aceite.

## 2. Impacto arquitetural

Cadastro passa pelo proxy e pelo middleware de identidade de apartamentos. A verificação de conta elegível consulta `users` por fronteira interna. Reservas, visitantes e futuros pedidos de agente se referem à unidade registrada no próprio domínio.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0001](../../adr/ADR-0001-servicos-por-dominio-e-camadas.md), [ADR-0002](../../adr/ADR-0002-orm-e-integridade-transacional.md), [ADR-0003](../../adr/ADR-0003-identidade-central-e-autorizacao-por-recurso.md).

O número é único e normalizado em maiúsculas, com até dez dígitos e uma letra opcional. A unidade tem um código interno persistente, `id`, que permanece ao editar o número. A edição troca o número enquanto a unidade estiver sem histórico. Referências impedem alteração da chave usada por reservas, visitas ou sessões. O vínculo é opcional e aceita usuário do tipo Morador em novas associações. Colisões e violações de dependência cancelam a escrita por rollback.

## 4. Visão de componentes

| Camada | Arquivo | Responsabilidade |
| --- | --- | --- |
| Router | services/apartments/routers/apartment_router.py | Receber DTO e identidade e chamar o controller |
| Controller | services/apartments/controllers/apartment_controller.py | Coordenar validação, persistência e serialização |
| Validator | services/apartments/validators/apartment_validator.py | Verificar permissão e regras da operação |
| Repository | services/apartments/repositories/apartment_repository.py | Consultar e escrever com SQLAlchemy em transação |
| Serializer | services/apartments/serializers/apartment_serializer.py | Produzir DTO público sem campos internos |
| Composição | services/apartments/main.py | Montar routers, middleware, Swagger e health do toolkit |

As schemas Pydantic validam tipo e formato. Validators não gravam e controllers não acessam Session ou engine. O repository aplica flush, locks e constraints conforme a operação. Falha faz rollback. A documentação OpenAPI declara os contratos de entrada, saída, erros e autenticação.

## 5. Contratos de interface

GET e POST em `/api/admin/apartments`. O cadastro recebe `number` e `resident_id` opcional. PATCH e DELETE em `/api/admin/apartments/{number}` fazem edição do número ou vínculo e exclusão sujeita à integridade. GET no mesmo caminho devolve o cadastro para a administração. GET em `/api/resident/apartments` devolve somente unidades da conta autenticada. A projeção administrativa fornece `id`, `number` e `resident_id`. O campo `resident_id` projeta o vínculo para o painel mostrar o nome do usuário responsável.

Número repetido gera conflito. Conta inexistente ou com papel incompatível rejeita o vínculo. A ativação do login é gerenciada separadamente. A tentativa de excluir unidade referenciada preserva os registros dependentes e informa o motivo. A falha da identidade não autoriza a mutação.

## 6. Modelo de dados

A tabela `apartments` guarda `id` e `number`. A relação `apartment_residents` usa o código da unidade para apontar a um usuário morador. A importação inicial usa número e nome de `apartamentos.json` para preencher unidade, usuário e relação. A atualização dos volumes anteriores conserva vínculos explícitos e mantém a titularidade conhecida de reservas e visitas.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F02-AC01 | Base. Cadastrar uma unidade, editar uma segunda e consultar a API de unidades com credenciais do morador. | O painel associa duas unidades à mesma conta e ambas aparecem na lista própria do morador. |
| F02-AC02 | Base. Criar uma unidade, repetir POST com vínculo diferente e comparar o estado obtido por GET. | A tentativa duplicada retorna conflito e preserva a unidade original. |
| F02-AC03 | Base. Tentar criar e editar unidades como morador, em seguida comparar a lista administrativa. | As operações administrativas são recusadas sem persistir alterações. |
| F02-AC04 | Base. Tentar DELETE sobre unidade de fixture com dependência e consultar a unidade e a agenda. | A exclusão é bloqueada e o histórico fica disponível. |
| F02-AC05 | Base. Conferir usuários e apartamentos importados e consultar uma unidade de teste após renumerá-la. | A carga associa o usuário morador da fonte à unidade, e o código da unidade editada se mantém após alterar o número. |
| F02-SEC01 | Base. Comparar GET de unidades do morador a duas unidades administrativas. | A consulta pessoal não devolve unidades de outras contas. |
| NFR01-AC01 | Base: HTTP real. Dado QA_A autenticado como resident e apartamento 9101 vinculado a QA_A; quando enviar PATCH /api/admin/apartments/9101 com number=9199 usando QA_A e consultar 9101 como QA_ADMIN. | Então PATCH retorna 403 e a consulta administrativa conserva número e vínculo originais. |
| NFR03-AC01 | Base: HTTP real. Dado 9101 pertence a QA_A e 9102 a QA_B; quando consultar GET /api/resident/apartments com QA_A e inspecionar resposta e log sanitizado. | Então lista contém 9101, não contém 9102 nem campos password_hash, credenciais ou bearer. |
