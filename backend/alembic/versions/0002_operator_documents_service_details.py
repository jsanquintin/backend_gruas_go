"""Operator documentation and service-specific fields; retain existing data.

Revision ID: 0002_documents
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_documents'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

def upgrade():
    # 0001 creó sus tablas desde Base.metadata; detectamos estructuras ya
    # existentes para soportar instalaciones nuevas y las de v0.1 sin pérdida.
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing = {col['name'] for col in inspector.get_columns('operators')}
    columns = [
        sa.Column('verification_status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('license_number', sa.String(length=80), nullable=True),
        sa.Column('license_expires_on', sa.Date(), nullable=True),
        sa.Column('registration_reference', sa.String(length=120), nullable=True),
        sa.Column('insurance_policy', sa.String(length=120), nullable=True),
        sa.Column('insurance_expires_on', sa.Date(), nullable=True),
    ]
    for column in columns:
        if column.name not in existing:
            op.add_column('operators', column)
    # Conserva operadores y servicios pero obliga a verificar de nuevo documentos.
    op.execute("UPDATE operators SET verified = false, verification_status = 'pending', verified_by = NULL, verified_at = NULL")
    if 'operator_reviews' not in inspector.get_table_names():
        op.create_table('operator_reviews',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('operator_id', sa.Integer(), sa.ForeignKey('operators.id'), nullable=False),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('action', sa.String(length=30), nullable=False),
            sa.Column('note', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_operator_reviews_operator_id', 'operator_reviews', ['operator_id'])
    service_cols = {col['name'] for col in inspector.get_columns('services')}
    for name, kind in [('recipient_name', sa.String(120)), ('recipient_phone', sa.String(40)),
                       ('package_description', sa.String(500)), ('vehicle_plate', sa.String(20)),
                       ('vehicle_description', sa.String(200))]:
        if name not in service_cols:
            op.add_column('services', sa.Column(name, kind, nullable=True))

def downgrade():
    for column in ['vehicle_description','vehicle_plate','package_description','recipient_phone','recipient_name']:
        op.drop_column('services', column)
    op.drop_index('ix_operator_reviews_operator_id', table_name='operator_reviews')
    op.drop_table('operator_reviews')
    for column in ['insurance_expires_on','insurance_policy','registration_reference','license_expires_on','license_number','verification_status']:
        op.drop_column('operators', column)
