# F01 — Fundação executável

Domínio: Operação | Onda: 1 | Prioridade: 1

Conforms to: NFR04, NFR02

## Descrição

Distribuir uma base local que compile, inicie e permita verificar separadamente as superfícies de identidade, cadastros, interface e futura integração do agente.

Como operador, quero subir o ambiente local com um comando para testar o produto sem configurar um provedor de modelos.

A referência de produto original é FR01. A correspondência dos critérios anteriores é F01-AC01 ↔ FR01/AC01, F01-AC02 ↔ FR01/AC02, F01-AC03 ↔ FR01/AC03. O aceite de prontidão da base foi separado da futura entrada acadêmica, agora testada em F10. Critérios adicionais descrevem verificações específicas desta separação de etapas.

## Capacidades

- Consumes: nenhuma.
- Provides: Interface React compilada, proxy de mesma origem, rotas privadas, dependências com prontidão e persistência local.
- Integração: O navegador chama o proxy em uma única origem. O proxy direciona autenticação, usuários e condomínio para serviços na rede do Compose. As bases e a fronteira interna do agente ficam na rede privada. A porta de avaliação acadêmica tem sua própria entrada futura, sem compartilhar o proxy de produto.

## Comportamento esperado

- **Dado** um clone com Docker e o cliente Compose e os dados iniciais
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** a composição inicia as onze unidades e carrega a tela de login.

- **Dado** uma configuração obrigatória de autenticação ausente numa composição descartável
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** o Compose recusa a configuração ou a autenticação fica sem prontidão. A falha identifica a variável sem divulgar segredo.

- **Dado** uma edição persistida em volume existente
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** a edição continua após reiniciar e a carga inicial não a sobrescreve.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F01-AC01 | Um clone com Docker e o cliente Compose e os dados iniciais | A composição inicia as onze unidades e carrega a tela de login | Validar o manifesto, subir a composição de teste, conferir serviços saudáveis e abrir a origem publicada |
| F01-AC02 | Uma configuração obrigatória de autenticação ausente numa composição descartável | O Compose recusa a configuração ou a autenticação fica sem prontidão. A falha identifica a variável sem divulgar segredo | Omitir a configuração em sandbox e comparar status do serviço e saída sanitizada |
| F01-AC03 | Uma edição persistida em volume existente | A edição continua após reiniciar e a carga inicial não a sobrescreve | Criar uma conta e alterar um cadastro, reiniciar os serviços e consultar os dois pelas mesmas APIs |
| F01-AC04 | Uma aplicação criada pela biblioteca e uma chamada válida, recusada ou com erro | A resposta mantém correlação, falhas não expõem payloads e os logs contêm apenas os campos operacionais permitidos | Executar os testes HTTP da biblioteca e conferir os serviços com chamadas autenticadas |
| F01-AC05 | Cadastros iniciais ausentes ou já importados e acesso administrativo válido | O importador usa as APIs e a repetição não duplica usuários, apartamentos ou áreas | Executar dados/importar_cadastros.py em ambiente de QA e comparar registros e JSONs antes e depois |
| F01-AC06 | Serviços construídos com o padrão FastAPI e toolkit | Cada domínio tem camadas separadas, escritas ORM, health centralizado e documentação OpenAPI | Executar o gate de camadas e conferir health, Swagger e schemas dos oito serviços |

A etapa de cada prova está identificada na [spec desta funcionalidade](../../specs/F01-fundacao/spec.md#7-estratégia-de-testes).


## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F01-SEC01 | Fronteiras e escopo | O proxy expõe caminhos públicos e privados esperados e mantém as rotas internas fechadas | Consultar a superfície pública de desenvolvimento e confirmar que a rota interna não está exposta |

## Fora do escopo

Publicação em produção, provedores de identidade externos e ativação do avaliador acadêmico entram em fluxos próprios.

## Tratamento de erros

Configuração obrigatória ausente ou banco inacessível impedem prontidão da dependência. O diagnóstico indica a falha sem imprimir credenciais. Uma indisponibilidade da fronteira do agente afeta a mensagem de chat e deixa os cadastros disponíveis.
