"""Transporte AI Studio com destino fixo e TLS obrigatório."""

import httpx
import ssl
import certifi

AI_STUDIO_BASE_URL = "https://generativelanguage.googleapis.com"


def enforce_ai_studio(request):
    if (
        request.url.scheme != "https"
        or request.url.host != "generativelanguage.googleapis.com"
        or request.url.port not in (None, 443)
        or request.url.userinfo
    ):
        raise ValueError("Destino do provedor não permitido.")


async def enforce_ai_studio_async(request):
    enforce_ai_studio(request)


def provider_ssl_context():
    # cafile explícito impede consulta a SSL_CERT_FILE/SSL_CERT_DIR. Nunca
    # desabilitar hostname checking ou CERT_REQUIRED para contornar o ambiente.
    return ssl.create_default_context(cafile=certifi.where())


def create_provider_clients():
    # Não herdar proxy/CA do ambiente; TLS continua verificado com trust store
    # padrão httpx. Redirecionamento não pode reenviar chave a outro host.
    context = provider_ssl_context()
    return (
        httpx.Client(
            trust_env=False,
            verify=context,
            follow_redirects=False,
            timeout=15,
            event_hooks={"request": [enforce_ai_studio]},
        ),
        httpx.AsyncClient(
            trust_env=False,
            verify=context,
            follow_redirects=False,
            timeout=15,
            event_hooks={"request": [enforce_ai_studio_async]},
        ),
    )
