"""Correspondência de rotas compartilhada pela autenticação e pelo OpenAPI."""


def application_path(scope: dict) -> str:
    """Retira apenas o prefixo root_path acrescentado pelo gateway ASGI."""
    path = scope.get("path", "/")
    root = scope.get("root_path", "").rstrip("/")
    return path[len(root) :] if root and path.startswith(root + "/") else path


def matches_path(path: str, prefixes) -> bool:
    """Compara segmentos: /private não protege acidentalmente /private-other."""
    return any(
        prefix == "/" or path == prefix or path.startswith(prefix + "/")
        for prefix in prefixes
    )


def route_template(scope: dict) -> str:
    """Obtém o template mesmo numa recusa antes do roteamento, sem logar IDs."""
    route = scope.get("route")
    if route is not None:
        return getattr(route, "path", "unmatched")
    from starlette.routing import Match

    partial = None
    for candidate in getattr(scope.get("app"), "routes", ()):
        match, _ = candidate.matches(scope)
        if match == Match.FULL:
            return getattr(candidate, "path", "unmatched")
        if match == Match.PARTIAL and partial is None:
            partial = candidate
    return getattr(partial, "path", "unmatched")
