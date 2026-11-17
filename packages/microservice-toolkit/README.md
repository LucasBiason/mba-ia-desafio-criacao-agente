# Microservice Toolkit

Biblioteca independente para preparar serviços FastAPI com autenticação configurável, erros seguros e logs JSON de requisições.

~~~python
from microservice_toolkit import create_app

app = create_app(title="Catálogo", service_name="catalogo")
~~~

Para proteger rotas, passe um verificador de bearer token em verifier e os caminhos em protected_paths. O verificador resolve uma identidade em dict ou lança HTTPException. A identidade fica em request.state.user. Cada serviço continua responsável por suas permissões de domínio.

O middleware ASGI propaga X-Request-ID e registra serviço, método, template da rota, status e duração. Cabeçalhos, payloads, query strings e detalhes de exceção ficam fora do log HTTP. Validação retorna campos e códigos sem os valores enviados. Erros inesperados recebem uma mensagem pública fixa.

O ServiceClient propaga a correlação e aceita catálogo explícito de destinos e um provedor de credencial interna. Não há configuração específica de condomínio na biblioteca.

## Desenvolvimento

Execute uv sync e uv run pytest. Para empacotar, use uv build.

A primeira versão contém a fundação HTTP. Políticas de negócio, armazenamento, cadastro de usuários e emissão de JWT pertencem às aplicações consumidoras.


## Saúde, documentação e persistência

create_app registra /health e aceita health_check para a prontidão específica. A função pode lançar HTTPException com 503 para uma dependência indisponível. Swagger em /docs e o contrato em /openapi.json são oferecidos pela aplicação. O contrato descreve bearer nas rotas protegidas e header de serviço configurável nas rotas internas.

Database fornece sessões SQLAlchemy e Repository controla commit, rollback e fechamento. As aplicações definem seus próprios modelos, validators, repositories e serializers. Conexões e opções de driver são configuradas pela aplicação consumidora.
