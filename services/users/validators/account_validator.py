from microservice_toolkit import error

from services.permissions import require_admin


class AccountValidator:
    def __init__(self, repository):
        self.repository = repository

    def validate_read(self, actor):
        if actor is not None:
            require_admin(actor)

    def administration(self, actor):
        require_admin(actor)
        self.repository.lock_administration()
        fresh = self.repository.get(actor["id"])
        if fresh is None or not fresh.active or fresh.role != "admin":
            raise error(403, "ADMIN_REQUIRED", "Operação reservada à administração.")

    def validate_create(self, data, actor):
        self.administration(actor)
        if self.repository.email_owner(data.email) is not None:
            raise error(409, "EMAIL_IN_USE", "Este e-mail já está cadastrado.")

    def existing(self, user_id, *, lock=False):
        account = self.repository.get(user_id, lock=lock)
        if account is None:
            raise error(404, "USER_NOT_FOUND", "Usuário não encontrado.")
        return account

    def validate_update(self, actor, user_id, values):
        self.administration(actor)
        if not values or any(value is None for value in values.values()):
            raise error(422, "INVALID_UPDATE", "Informe um ou mais campos válidos.")
        account = self.existing(user_id, lock=True)
        owner = self.repository.email_owner(values.get("email", account.email))
        if owner is not None and owner != user_id:
            raise error(409, "EMAIL_IN_USE", "Este e-mail já está cadastrado.")
        if values.get("role", account.role) != account.role:
            raise error(409, "ROLE_IMMUTABLE", "O perfil da conta é definido no cadastro.")
        if (account.role == "admin" and account.active and not values.get("active", account.active)
                and not self.repository.other_active_admin(user_id)):
            raise error(409, "LAST_ADMIN", "Mantenha pelo menos um administrador ativo.")
        return account
