"""create Better Auth tables (user, session, account, verification)

Revision ID: h01_better_auth
Revises: g83b1a4d7e02
Create Date: 2026-04-07 12:00:00.000000

Better Auth manages these tables directly — no SQLAlchemy models.
Raw SQL used to match the exact schema Better Auth expects.
"""
from typing import Sequence, Union
from alembic import op


revision: str = "h01_better_auth"
down_revision: Union[str, None] = "g83b1a4d7e02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS "user" (
            "id"            TEXT PRIMARY KEY,
            "name"          TEXT NOT NULL,
            "email"         TEXT NOT NULL UNIQUE,
            "emailVerified" BOOLEAN NOT NULL DEFAULT FALSE,
            "image"         TEXT,
            "createdAt"     TIMESTAMP NOT NULL DEFAULT NOW(),
            "updatedAt"     TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS "session" (
            "id"        TEXT PRIMARY KEY,
            "token"     TEXT NOT NULL UNIQUE,
            "userId"    TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
            "expiresAt" TIMESTAMP NOT NULL,
            "ipAddress" TEXT,
            "userAgent" TEXT,
            "createdAt" TIMESTAMP NOT NULL DEFAULT NOW(),
            "updatedAt" TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS "account" (
            "id"                    TEXT PRIMARY KEY,
            "userId"                TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
            "accountId"             TEXT NOT NULL,
            "providerId"            TEXT NOT NULL,
            "accessToken"           TEXT,
            "refreshToken"          TEXT,
            "accessTokenExpiresAt"  TIMESTAMP,
            "refreshTokenExpiresAt" TIMESTAMP,
            "scope"                 TEXT,
            "idToken"               TEXT,
            "password"              TEXT,
            "createdAt"             TIMESTAMP NOT NULL DEFAULT NOW(),
            "updatedAt"             TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS "verification" (
            "id"         TEXT PRIMARY KEY,
            "identifier" TEXT NOT NULL,
            "value"      TEXT NOT NULL,
            "expiresAt"  TIMESTAMP NOT NULL,
            "createdAt"  TIMESTAMP NOT NULL DEFAULT NOW(),
            "updatedAt"  TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS "verification"')
    op.execute('DROP TABLE IF EXISTS "account"')
    op.execute('DROP TABLE IF EXISTS "session"')
    op.execute('DROP TABLE IF EXISTS "user"')
