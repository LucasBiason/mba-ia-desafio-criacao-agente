from sqlalchemy import func, select

from microservice_toolkit import Repository
from services.users.models.account import Account
from services.authentication.models.login_session import LoginSession


class AccountRepository(Repository):
    def lock_administration(self):
        self.session.execute(select(func.pg_advisory_xact_lock(74109143)))

    def get(self, user_id, *, lock=False):
        return self.session.get(Account, user_id, with_for_update=lock)

    def list(self):
        return self.session.scalars(
            select(Account).order_by(Account.name, Account.id)
        ).all()

    def email_owner(self, email):
        return self.session.scalar(select(Account.id).where(Account.email == email))

    def other_active_admin(self, user_id):
        return self.session.scalar(
            select(Account.id)
            .where(
                Account.role == "admin",
                Account.active.is_(True),
                Account.id != user_id,
            )
            .limit(1)
        )

    def create(self, account):
        self.session.add(account)
        self.session.flush()
        return account

    def save(self, account, values):
        for key, value in values.items():
            setattr(account, key, value)
        self.session.flush()
        return account

    def revoke_sessions(self, user_id):
        for record in self.session.scalars(
            select(LoginSession).where(
                LoginSession.account_id == user_id,
                LoginSession.revoked_at.is_(None),
            )
        ):
            record.revoked_at = func.now()
