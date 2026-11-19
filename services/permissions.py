from microservice_toolkit import error


def require_admin(user):
    if user["role"] != "admin":
        raise error(403, "ADMIN_REQUIRED", "Operação reservada à administração.")


def require_resident(user):
    if user["role"] != "resident":
        raise error(403, "FORBIDDEN", "Esta operação é exclusiva do morador.")
