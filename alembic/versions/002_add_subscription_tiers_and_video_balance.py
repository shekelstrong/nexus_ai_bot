"""add subscription tiers and video balance

Revision ID: 002
Revises: 001
Create Date: 2026-03-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем новое поле video_generations_balance
    op.add_column('users', sa.Column('video_generations_balance', sa.Integer(), nullable=False, server_default='0'))
    
    # Обновляем subscription_tier для старых записей (PREMIUM -> PRO, PREMIUM_X2 -> ELITE)
    # Это маппинг для обратной совместимости
    op.execute("""
        UPDATE users 
        SET subscription_tier = 'PRO' 
        WHERE subscription_tier = 'PREMIUM'
    """)
    op.execute("""
        UPDATE users 
        SET subscription_tier = 'ELITE' 
        WHERE subscription_tier = 'PREMIUM_X2'
    """)


def downgrade() -> None:
    # Откатываем изменения subscription_tier
    op.execute("""
        UPDATE users 
        SET subscription_tier = 'PREMIUM' 
        WHERE subscription_tier = 'PRO'
    """)
    op.execute("""
        UPDATE users 
        SET subscription_tier = 'PREMIUM_X2' 
        WHERE subscription_tier = 'ELITE'
    """)
    
    # Удаляем поле video_generations_balance
    op.drop_column('users', 'video_generations_balance')
