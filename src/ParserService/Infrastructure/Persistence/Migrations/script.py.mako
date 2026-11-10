"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


class Migration:
    """Rename this class to match the file name and describe the change."""

    def upgrade(self) -> None:
        """Apply the change."""
        ${upgrades if upgrades else "pass"}

    def downgrade(self) -> None:
        """Revert the change."""
        ${downgrades if downgrades else "pass"}


upgrade = Migration().upgrade
downgrade = Migration().downgrade
