from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from microservice_toolkit import Repository
from services.users.models.account import Account
from services.authentication.models.login_session import LoginSession
from services.authentication.models.login_limit import LoginLimit


class SessionRepository(Repository):
    def register_attempt(self, key):
        now = datetime.now(UTC)
        self.session.execute(
            delete(LoginLimit).where(LoginLimit.window_start < now - timedelta(days=1))
        )
        statement = insert(LoginLimit).values(key=key, window_start=now, attempts=1)
        from sqlalchemy import case

        statement = statement.on_conflict_do_update(
            index_elements=[LoginLimit.key],
            set_={
                "attempts": case(
                    (LoginLimit.window_start < now - timedelta(minutes=15), 1),
                    else_=LoginLimit.attempts + 1,
                ),
                "window_start": case(
                    (LoginLimit.window_start < now - timedelta(minutes=15), now),
                    else_=LoginLimit.window_start,
                ),
            },
        ).returning(LoginLimit.attempts)
        return self.session.scalar(statement)

    def account_by_email(self, email):
        return self.session.scalar(select(Account).where(Account.email == email))

    def locked_account(self, user_id):
        return self.session.get(
            Account, user_id, with_for_update=True, populate_existing=True
        )

    def create(self, record, bucket):
        self.session.execute(
            delete(LoginSession).where(LoginSession.expires_at < datetime.now(UTC))
        )
        self.session.add(record)
        self.session.execute(delete(LoginLimit).where(LoginLimit.key == bucket))
        self.session.flush()

    def identity(self, claims):
        return self.session.scalar(
            select(Account)
            .join(LoginSession, LoginSession.account_id == Account.id)
            .where(
                LoginSession.id == claims["jti"],
                LoginSession.account_id == claims["sub"],
                LoginSession.revoked_at.is_(None),
                LoginSession.expires_at > datetime.now(UTC),
                Account.active.is_(True),
            )
        )

    def revoke(self, session_id):
        record = self.session.get(LoginSession, session_id, with_for_update=True)
        if record is not None and record.revoked_at is None:
            record.revoked_at = datetime.now(UTC)
