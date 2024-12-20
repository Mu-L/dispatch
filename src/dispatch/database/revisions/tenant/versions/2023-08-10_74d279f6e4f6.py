"""Adds column to indicate if health metrics need to be collected for the service

Revision ID: 74d279f6e4f6
Revises: 6b98c28edd86
Create Date: 2023-03-29 13:51:11.269860

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "74d279f6e4f6"
down_revision = "6b98c28edd86"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("service", sa.Column("health_metrics", sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("service", "health_metrics")
    # ### end Alembic commands ###
