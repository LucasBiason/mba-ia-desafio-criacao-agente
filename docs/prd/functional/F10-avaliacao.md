# F10 — Compatibilidade e aceite acadêmico

Domínio: Integração | Onda: 7 | Prioridade: 1

Requisitos não funcionais relacionados: NFR04, NFR01, NFR03

## Descrição

A API acadêmica está implementada separadamente da base. O aceite integral depende dos 15 passos em clone limpo com Gemini real e publicação do corte aprovado.

Entregar as seis rotas do enunciado, comandos de restauração e subida e evidência do roteiro completo, preservando as cinco garantias.

Como avaliador, quero executar o protocolo documentado em ambiente local isolado e verificar as garantias pelas rotas e pelos dados.

A referência de produto original é FR10. A correspondência dos critérios anteriores é F10-AC01 ↔ FR10/AC01, F10-AC02 ↔ FR10/AC02, F10-AC03 ↔ FR10/AC03. Critérios adicionais descrevem verificações específicas desta separação de etapas.

## Capacidades

- Depende de: F09.
- Fornece: Contrato de integração, preparação e medição do protocolo acadêmico independente da entrada autenticada do produto.
- Integração: Um entrypoint dedicado traduz o protocolo acadêmico para a mesma lógica de sessão, reconhecimento de intenções e regras de domínio. O modo fica isolado da composição de produto. O adaptador de verificação acadêmica poderá consultar projeções por apartamento definidas no protocolo. A rede do produto não roteia esses caminhos.

## Comportamento esperado

- **Dado** um clone limpo com dependências e chave própria autorizada
- **Quando** seguir o roteiro de partida, restaurar os dados, registrar códigos e observar estado e eventos em cada passo
- **Então** o avaliador executa os 15 passos na porta 8000 com o protocolo completo.

- **Dado** a composição base do produto é consultada pelo proxy publicado
- **Quando** consultar rotas locais planejadas na origem do produto e tentar APIs privadas sem bearer
- **Então** caminhos acadêmicos e rotas internas não contornam a autenticação.

- **Dado** o fork está em preparação final após a aula
- **Quando** comparar hashes dos dados, revisar o lock e verificar os links das garantias
- **Então** cinco fixtures correspondem à origem e o README identifica provas e trechos implementados.

- **Dado** a base é construída e iniciada com seu comando de demonstração
- **Quando** conferir os hashes das fixtures antes da partida e depois do teste com volumes isolados
- **Então** as cinco fixtures mantêm o mesmo conteúdo entre a cópia e o ambiente inicializado.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F10-AC01 | Um clone limpo com dependências e chave própria autorizada | O avaliador executa os 15 passos na porta 8000 com o protocolo completo | Seguir o roteiro de partida, restaurar os dados, registrar códigos e observar estado e eventos em cada passo |
| F10-AC02 | A composição base do produto é consultada pelo proxy publicado | Caminhos acadêmicos e rotas internas não contornam a autenticação | Consultar rotas locais planejadas na origem do produto e tentar APIs privadas sem bearer |
| F10-AC03 | O fork está em preparação final após a aula | Cinco fixtures correspondem à origem e o README identifica provas e trechos implementados | Comparar hashes dos dados, revisar o lock e verificar os links das garantias |
| F10-AC04 | A base é construída e iniciada com seu comando de demonstração | As cinco fixtures mantêm o mesmo conteúdo entre a cópia e o ambiente inicializado | Conferir os hashes das fixtures antes da partida e depois do teste com volumes isolados |

A etapa de cada prova está identificada na [spec desta funcionalidade](../../specs/F10-avaliacao/spec.md#7-estratégia-de-testes).

## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F10-SEC01 | Fronteiras e escopo | O exercício roda localmente, com dados separados e sem publicar segredos | Conferir bind, isolamento de armazenamento, rota de autenticação do produto e diff de configuração |

## Fora do escopo

Publicação do fork, instalação de credenciais e execução dos 15 passos dependem da implementação didática do agente. Nenhum acesso sem autenticação é oferecido pelo produto para imitar a avaliação.

## Tratamento de erros

Sessão ausente gera 404; decisão sequencial inexistente, consumida ou de outra sessão gera 409 sem alteração. Falha de dependência informa indisponibilidade e preserva estado. A implantação não pode indicar execução do avaliador enquanto o entrypoint estiver ausente.
