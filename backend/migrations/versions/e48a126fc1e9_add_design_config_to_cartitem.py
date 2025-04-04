"""Add design_config to CartItem

Revision ID: e48a126fc1e9
Revises: 5b8668d53929
Create Date: 2024-11-25 00:41:04.835999

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e48a126fc1e9'
down_revision = '5b8668d53929'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('cart_items', schema=None) as batch_op:
        batch_op.alter_column('design_config',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment=None,
               existing_comment='{position, scale, rotation}',
               existing_nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('cart_items', schema=None) as batch_op:
        batch_op.alter_column('design_config',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               comment='{position, scale, rotation}',
               existing_nullable=True)

    # ### end Alembic commands ###
