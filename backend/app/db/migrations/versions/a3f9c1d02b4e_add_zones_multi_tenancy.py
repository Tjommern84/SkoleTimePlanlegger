"""add zones multi-tenancy

Revision ID: a3f9c1d02b4e
Revises: 1e68749da17e
Create Date: 2026-07-12 00:00:00.000000

Introduces `zones` / `zone_memberships` / `zone_invitations` and scopes the
two root entities (`school_years`, `teachers`) to a zone. Everything else
(subjects, activities, generated timetables, ...) inherits zone scoping
transitively through their existing FK to `school_years` or `teachers`.

Backfills all pre-existing data into a single zone owned by the first
email in the current ALLOWED_EMAILS setting, with any remaining configured
emails added as members (or, if that user hasn't logged in yet, as a
pending invitation that the existing login flow will auto-accept).

NOTE for the operator running this against the real production database:
the `school_years_label_key` / `teachers_initials_key` constraint names
below are SQLAlchemy/Postgres's *default* auto-generated names for the
unnamed `UniqueConstraint("label")` / `UniqueConstraint("initials")` in the
previous schema -- verify these are the actual names in production (e.g.
via `\\d school_years` / `\\d teachers` in psql) before running this
migration there. They do not need verification for SQLite (local dev),
which recreates the table via batch mode regardless of constraint naming.
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.config import settings

# revision identifiers, used by Alembic.
revision: str = 'a3f9c1d02b4e'
down_revision: Union[str, Sequence[str], None] = '1e68749da17e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # --- 1. New tables -----------------------------------------------------
    op.create_table(
        'zones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'zone_memberships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('zone_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.Enum('OWNER', 'MEMBER', name='zonerole'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['zone_id'], ['zones.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('zone_id', 'user_id'),
    )
    op.create_table(
        'zone_invitations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('zone_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('invited_by_user_id', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'ACCEPTED', 'REVOKED', name='zoneinvitationstatus'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['zone_id'], ['zones.id']),
        sa.ForeignKeyConstraint(['invited_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_zone_invitations_email_status', 'zone_invitations', ['email', 'status']
    )

    # --- 2. Add nullable zone_id columns ------------------------------------
    with op.batch_alter_table('school_years') as batch_op:
        batch_op.add_column(sa.Column('zone_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_school_years_zone_id', 'zones', ['zone_id'], ['id']
        )
    with op.batch_alter_table('teachers') as batch_op:
        batch_op.add_column(sa.Column('zone_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_teachers_zone_id', 'zones', ['zone_id'], ['id'])

    # --- 3. Backfill ---------------------------------------------------------
    zones = sa.table('zones', sa.column('id'), sa.column('name'), sa.column('created_at'))
    users = sa.table('users', sa.column('id'), sa.column('email'))
    memberships = sa.table(
        'zone_memberships',
        sa.column('zone_id'),
        sa.column('user_id'),
        sa.column('role'),
        sa.column('created_at'),
    )
    invitations = sa.table(
        'zone_invitations',
        sa.column('zone_id'),
        sa.column('email'),
        sa.column('invited_by_user_id'),
        sa.column('status'),
        sa.column('created_at'),
    )
    school_years_t = sa.table('school_years', sa.column('zone_id'))
    teachers_t = sa.table('teachers', sa.column('zone_id'))

    emails = settings.allowed_emails_list
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if emails:
        owner_email = emails[0]
        owner_row = bind.execute(
            sa.select(users.c.id).where(users.c.email == owner_email)
        ).first()
        if owner_row is None:
            raise RuntimeError(
                f"Expected a users row for {owner_email!r} (first entry of "
                "ALLOWED_EMAILS) to already exist -- log in once as this "
                "user before running this migration."
            )
        owner_id = owner_row[0]

        zone_id = bind.execute(
            sa.insert(zones).values(name="Min sone", created_at=now).returning(zones.c.id)
        ).scalar_one()

        bind.execute(
            sa.insert(memberships).values(
                zone_id=zone_id, user_id=owner_id, role="OWNER", created_at=now
            )
        )

        for member_email in emails[1:]:
            member_row = bind.execute(
                sa.select(users.c.id).where(users.c.email == member_email)
            ).first()
            if member_row is not None:
                bind.execute(
                    sa.insert(memberships).values(
                        zone_id=zone_id, user_id=member_row[0], role="MEMBER", created_at=now
                    )
                )
            else:
                bind.execute(
                    sa.insert(invitations).values(
                        zone_id=zone_id,
                        email=member_email.lower(),
                        invited_by_user_id=owner_id,
                        status="PENDING",
                        created_at=now,
                    )
                )

        bind.execute(sa.update(school_years_t).values(zone_id=zone_id))
        bind.execute(sa.update(teachers_t).values(zone_id=zone_id))
    # If ALLOWED_EMAILS is empty, there is no pre-existing user to own the
    # data; this only happens on a brand-new, still-empty database, so
    # school_years/teachers have no rows to backfill.

    # --- 4. Make zone_id non-nullable, replace global-unique constraints -----
    # SQLite's original inline `UNIQUE (label)` / `UNIQUE (initials)` were
    # created without a name (confirmed via `inspect(engine).get_unique_
    # constraints(...)` -> name=None), so batch mode needs an explicit
    # naming_convention to be able to address them for dropping -- this is
    # the standard Alembic workaround for unnamed SQLite constraints.
    # Postgres constraints already have a real, addressable name.
    sqlite_uq_naming = {"uq": "uq_%(table_name)s_%(column_0_name)s"}

    with op.batch_alter_table(
        'school_years', naming_convention=sqlite_uq_naming if is_sqlite else None
    ) as batch_op:
        batch_op.alter_column('zone_id', nullable=False)
        batch_op.drop_constraint(
            'uq_school_years_label' if is_sqlite else 'school_years_label_key',
            type_='unique',
        )
        batch_op.create_unique_constraint(
            'uq_school_years_zone_id_label', ['zone_id', 'label']
        )
    with op.batch_alter_table(
        'teachers', naming_convention=sqlite_uq_naming if is_sqlite else None
    ) as batch_op:
        batch_op.alter_column('zone_id', nullable=False)
        batch_op.drop_constraint(
            'uq_teachers_initials' if is_sqlite else 'teachers_initials_key',
            type_='unique',
        )
        batch_op.create_unique_constraint(
            'uq_teachers_zone_id_initials', ['zone_id', 'initials']
        )


def downgrade() -> None:
    with op.batch_alter_table('teachers') as batch_op:
        batch_op.drop_constraint('uq_teachers_zone_id_initials', type_='unique')
        batch_op.create_unique_constraint('teachers_initials_key', ['initials'])
        batch_op.alter_column('zone_id', nullable=True)
        batch_op.drop_constraint('fk_teachers_zone_id', type_='foreignkey')
        batch_op.drop_column('zone_id')
    with op.batch_alter_table('school_years') as batch_op:
        batch_op.drop_constraint('uq_school_years_zone_id_label', type_='unique')
        batch_op.create_unique_constraint('school_years_label_key', ['label'])
        batch_op.alter_column('zone_id', nullable=True)
        batch_op.drop_constraint('fk_school_years_zone_id', type_='foreignkey')
        batch_op.drop_column('zone_id')

    op.drop_index('ix_zone_invitations_email_status', table_name='zone_invitations')
    op.drop_table('zone_invitations')
    op.drop_table('zone_memberships')
    op.drop_table('zones')

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        sa.Enum(name='zoneinvitationstatus').drop(bind, checkfirst=True)
        sa.Enum(name='zonerole').drop(bind, checkfirst=True)
