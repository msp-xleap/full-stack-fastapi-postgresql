"""Initialize models

Revision ID: bf7b226caa17
Revises: 
Create Date: 2024-03-19 13:25:42.660816

"""
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = 'bf7b226caa17'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # Create AI Agent Table
    op.create_table('ai_agent',
    sa.Column('api_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('model', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('api_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('api_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('org_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('server_address', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('session_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('workspace_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('instance_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('secret', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_aiagent_id'), 'ai_agent', ['id'], unique=False)
    op.create_index(op.f('ix_aiagent_instance_id'), 'ai_agent',
                    ['instance_id'], unique=True)

    # Create User Table
    op.create_table('user',
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_superuser', sa.Boolean(), nullable=False),
    sa.Column('full_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('hashed_password', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)

    # Create Idea Table
    op.create_table('idea',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('text', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('folder_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('created_by_ai', sa.Boolean(), nullable=False),
    sa.Column('created_by', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('idea_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
    sa.Column('agent_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('idea_count', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['agent_id'], ['ai_agent.id'], ),
    sa.PrimaryKeyConstraint('idea_id')
    )
    op.create_index(op.f('ix_idea_idea_id'), 'idea', ['idea_id'], unique=False)

    # Create Briefing Table
    op.create_table('briefing',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('frequency', sa.Integer(), nullable=False),
    sa.Column('question', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('topic', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('briefing_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
    sa.Column('agent_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
    sa.ForeignKeyConstraint(['agent_id'], ['ai_agent.id'], ),
    sa.PrimaryKeyConstraint('briefing_id')
    )
    op.create_index(op.f('ix_briefing_briefing_id'), 'briefing',
                    ['briefing_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_idea_idea_id'), table_name='idea')
    op.drop_table('idea')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_table('user')
    op.drop_index(op.f('ix_aiagent_instance_id'), table_name='ai_agent')
    op.drop_index(op.f('ix_aiagent_id'), table_name='ai_agent')
    op.drop_table('ai_agent')
    # ### end Alembic commands ###
