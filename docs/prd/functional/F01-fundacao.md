# F01 — Fundação executável

Domínio: Operação | Onda: 1 | Prioridade: 1

Requisitos não funcionais relacionados: NFR04, NFR02

## Descrição

Distribuir uma base local que compile, inicie e permita verificar separadamente as superfícies de identidade, cadastros, interface e integração opcional do agente.

Como operador, quero subir o ambiente local com um comando para testar o produto sem configurar um provedor de modelos.

A referência de produto original é FR01. A correspondência dos critérios anteriores é F01-AC01 ↔ FR01/AC01, F01-AC02 ↔ FR01/AC02, F01-AC03 ↔ FR01/AC03. O aceite de prontidão da base foi separado da futura entrada acadêmica, agora testada em F10. Critérios adicionais descrevem verificações específicas desta separação de etapas.

## Capacidades

- Depende de: nenhuma.
- Fornece: Interface React compilada, proxy de mesma origem, rotas privadas, dependências com prontidão e persistência local.
- Integração: O navegador chama o proxy em uma única origem. O proxy direciona autenticação, usuários e condomínio para serviços na rede do Compose. As bases e a fronteira interna do agente ficam na rede privada. A porta de avaliação acadêmica tem sua própria entrada futura, sem compartilhar o proxy de produto.

## Comportamento esperado

- **Dado** um clone com Docker e o cliente Compose e os dados iniciais
- **Quando** validar o manifesto, subir os dois jobs de preparação e a composição de teste, conferir os onze serviços contínuos saudáveis e abrir a origem publicada
- **Então** a composição inicia as onze unidades e carrega a tela de login.

- **Dado** uma configuração obrigatória de autenticação ausente numa composição descartável
- **Quando** omitir a configuração em sandbox e comparar status do serviço e saída sanitizada
- **Então** o Compose recusa a configuração ou a autenticação fica sem prontidão. A falha identifica a variável sem divulgar segredo.

- **Dado** uma edição persistida em volume existente
- **Quando** criar uma conta e alterar um cadastro, reiniciar os serviços e consultar os dois pelas mesmas APIs
- **Então** a edição continua após reiniciar e a carga inicial não a sobrescreve.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F01-AC01 | Um clone com Docker e o cliente Compose e os dados iniciais | A composição inicia as onze unidades e carrega a tela de login | Validar o manifesto, subir os dois jobs de preparação e a composição de teste, conferir os onze serviços contínuos saudáveis e abrir a origem publicada |
| F01-AC02 | Uma configuração obrigatória de autenticação ausente numa composição descartável | O Compose recusa a configuração ou a autenticação fica sem prontidão. A falha identifica a variável sem divulgar segredo | Omitir a configuração em sandbox e comparar status do serviço e saída sanitizada |
| F01-AC03 | Uma edição persistida em volume existente | A edição continua após reiniciar e a carga inicial não a sobrescreve | Criar uma conta e alterar um cadastro, reiniciar os serviços e consultar os dois pelas mesmas APIs |
| F01-AC04 | Uma aplicação criada pela biblioteca e uma chamada válida, recusada ou com erro | A resposta mantém correlação, falhas não expõem payloads e os logs contêm apenas os campos operacionais permitidos | Executar os testes HTTP da biblioteca e conferir os serviços com chamadas autenticadas |
| F01-AC05 | Cadastros iniciais ausentes ou já importados e acesso administrativo válido | O importador usa as APIs e a repetição não duplica usuários, apartamentos ou áreas | Executar tools/importar_cadastros.py em ambiente de QA e comparar registros e JSONs antes e depois |
| F01-AC06 | Serviços construídos com o padrão FastAPI e toolkit | Cada domínio tem camadas separadas, escritas ORM, health de liveness centralizado e documentação OpenAPI | Executar o gate de camadas, conferir Swagger e schemas dos oito serviços e consultar health com banco indisponível |

A etapa de cada prova está identificada na [spec desta funcionalidade](../../specs/F01-fundacao/spec.md#7-estratégia-de-testes).


## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F01-SEC01 | Fronteiras e escopo | O proxy expõe caminhos públicos e privados esperados e mantém as rotas internas fechadas | Consultar a superfície pública de desenvolvimento e confirmar que a rota interna não está exposta |

## Fora do escopo

Publicação em produção, provedores de identidade externos e ativação do avaliador acadêmico entram em fluxos próprios.

## Tratamento de erros

Configuração obrigatória ausente impede a partida. Banco inacessível impede a preparação inicial e retorna erro de dependência nas operações de negócio; o health de liveness permanece disponível. O diagnóstico indica a falha sem imprimir credenciais. Uma indisponibilidade da fronteira do agente afeta a mensagem de chat e deixa os cadastros disponíveis.
