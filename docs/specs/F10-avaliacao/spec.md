---
spec_template: 1
feature: F10
ceremony: full
prd_source: docs/prd/functional/F10-avaliacao.md
---

# F10 — Compatibilidade e aceite acadêmico

## 1. Visão técnica

A avaliação futura inicia na porta local 8000, usando Python 3.12 ou superior, uv com lock versionado, uma versão exata da série 2 de Google ADK e credencial do provedor somente no ambiente. O modo usa os arquivos iniciais intactos. É separado do proxy autenticado do produto. A base executável não habilita essa entrada.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F10](../../prd/functional/F10-avaliacao.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../design/architecture.md). Este documento especifica os contratos da base e das etapas da integração identificadas na matriz.

## 2. Impacto arquitetural

Um entrypoint dedicado traduz o protocolo acadêmico para a mesma lógica de sessão, reconhecimento de intenções e regras de domínio. O modo fica isolado da composição de produto. O adaptador de verificação acadêmica poderá consultar projeções por apartamento definidas no protocolo. A rede do produto não roteia esses caminhos.

## 3. Decisões técnicas

Reservar o contrato atual de produto com namespace /api e autenticação obrigatória. Adotar perfil ou entrypoint separado para o avaliador, com banco descartável exclusivo quando o teste for iniciado. Fixar a versão exata do ADK após verificar a retomada com sessão persistida. Executar restauração de dados como ação explícita do roteiro, fora da partida normal.

## 4. Visão de componentes

- Futuro entrypoint local de avaliação, separado do frontend e do proxy de produto.
- Adaptador de sessões, mensagens, eventos, decisões e projeções no formato do enunciado.
- Roteiro de confirmação, persistência e concorrência para registro das provas.
- Fixtures do desafio com auditoria de integridade do conteúdo.

## 5. Contratos de interface

| Método e rota prevista | Entrada | Resposta esperada |
| --- | --- | --- |
| POST `/sessoes` | `apartamento` string | 201 e `session_id` |
| POST `/sessoes/{session_id}/mensagens` | `texto` string | 200 e objeto com `resposta` e `confirmacoes_pendentes` |
| POST `/sessoes/{session_id}/confirmacoes` | `id` string e `confirmado` booleano | 200 com resposta e pendências, ou 409 para pendência inválida |
| GET `/sessoes/{session_id}/eventos` | Identificador da sessão | 200 com eventos completos em ordem |
| GET `/apartamentos/{numero}/reservas` | Número da unidade | 200 com lista de `codigo`, `area` e `data` |
| GET `/apartamentos/{numero}/visitantes` | Número da unidade | 200 com lista de `nome` e `data` |

Sessão inexistente nas suas rotas retorna 404. Datas usam AAAA-MM-DD. As pendências contêm `id`, `acao` e `detalhes`. O avaliador verifica projeções, eventos observados e exclusividade no instante da gravação.

Sessão ausente gera 404; decisão sequencial inexistente, consumida ou de outra sessão gera 409 sem alteração. Falha de dependência informa indisponibilidade e preserva estado. A implantação não pode indicar execução do avaliador enquanto o entrypoint estiver ausente.

## 6. Modelo de dados

A restauração acadêmica deve repor reservas e visitantes das fixtures e definir, no roteiro, o tratamento de sessões. A partida normal retém eventos e efeitos. O ambiente acadêmico deve usar isolamento lógico ou físico da persistência de produto.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F10-AC01 | Avaliação acadêmica. Seguir o roteiro de partida, restaurar os dados, registrar códigos e observar estado e eventos em cada passo. | O avaliador executa os 15 passos na porta 8000 com o protocolo completo. |
| F10-AC02 | Base. Consultar rotas locais planejadas na origem do produto e tentar APIs privadas sem bearer. | Caminhos acadêmicos e rotas internas não contornam a autenticação. |
| F10-AC03 | Avaliação acadêmica. Comparar hashes dos dados, revisar o lock e verificar os links das garantias. | Cinco fixtures correspondem à origem e o README identifica provas e trechos implementados. |
| F10-AC04 | Base. Conferir os hashes das fixtures antes da partida e depois do teste com volumes isolados. | As cinco fixtures mantêm o mesmo conteúdo entre a cópia e o ambiente inicializado. |
| F10-SEC01 | Avaliação acadêmica. Conferir bind, isolamento de armazenamento, rota de autenticação do produto e diff de configuração. | O exercício roda localmente, com dados separados e sem publicar segredos. |
| NFR01-AC01 | Avaliação acadêmica. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. | A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. |
| NFR03-AC01 | Avaliação acadêmica. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas. | A evidência não inclui segredos ou objetos de unidades fora da autorização. |
| NFR04-AC01 | Avaliação acadêmica. Executar o procedimento aplicável a partir de uma instalação isolada e registrar componentes, saídas e condições não exercitadas. | As dependências do modo escolhido atingem prontidão e os verificadores registram a condição observada. |
