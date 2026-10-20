"""Geolocation, tariffs, authenticated dispatch events (non-destructive).

Revision ID: 0003_dispatch
Revises: 0002_documents
"""
from alembic import op
import sqlalchemy as sa
revision='0003_dispatch'
down_revision='0002_documents'
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind()
    inspector=sa.inspect(bind)
    svc_cols={c['name'] for c in inspector.get_columns('services')}
    for col in ('destination_lat','destination_lng'):
        if col not in svc_cols:
            op.add_column('services',sa.Column(col,sa.Numeric(10,7),nullable=True))
    tables=inspector.get_table_names()
    if 'operator_locations' not in tables:
        op.create_table('operator_locations',
            sa.Column('id',sa.Integer(),primary_key=True),
            sa.Column('company_id',sa.Integer(),sa.ForeignKey('companies.id'),nullable=False),
            sa.Column('operator_id',sa.Integer(),sa.ForeignKey('operators.id'),nullable=False),
            sa.Column('lat',sa.Numeric(10,7),nullable=False),
            sa.Column('lng',sa.Numeric(10,7),nullable=False),
            sa.Column('accuracy_m',sa.Float(),nullable=False),
            sa.Column('recorded_at',sa.DateTime(timezone=True),nullable=False),
        )
        for col in ('company_id','operator_id','recorded_at'):
            op.create_index('ix_operator_locations_'+col,'operator_locations',[col])
    if 'tariffs' not in tables:
        op.create_table('tariffs',
            sa.Column('id',sa.Integer(),primary_key=True),
            sa.Column('company_id',sa.Integer(),sa.ForeignKey('companies.id'),nullable=False),
            sa.Column('kind',sa.String(20),nullable=False),
            sa.Column('service_type',sa.String(40),nullable=False),
            sa.Column('base_dop',sa.Numeric(12,2),nullable=False),
            sa.Column('per_km_dop',sa.Numeric(12,2),nullable=False),
            sa.Column('minimum_dop',sa.Numeric(12,2),nullable=False),
            sa.Column('operator_base_dop',sa.Numeric(12,2),nullable=False),
            sa.Column('active',sa.Boolean(),nullable=False),
            sa.Column('updated_by',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
            sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
            sa.UniqueConstraint('company_id','service_type',name='uq_tariff_company_service'),
        )
        op.create_index('ix_tariffs_company_id','tariffs',['company_id'])
    if 'dispatch_events' not in tables:
        op.create_table('dispatch_events',
            sa.Column('id',sa.Integer(),primary_key=True),
            sa.Column('company_id',sa.Integer(),sa.ForeignKey('companies.id'),nullable=False),
            sa.Column('kind',sa.String(30),nullable=False),
            sa.Column('ref_id',sa.Integer(),nullable=True),
            sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        )
        op.create_index('ix_dispatch_events_company_id','dispatch_events',['company_id'])

def downgrade():
    op.drop_index('ix_dispatch_events_company_id',table_name='dispatch_events')
    op.drop_table('dispatch_events')
    op.drop_index('ix_tariffs_company_id',table_name='tariffs')
    op.drop_table('tariffs')
    for col in ('company_id','operator_id','recorded_at'):
        op.drop_index('ix_operator_locations_'+col,table_name='operator_locations')
    op.drop_table('operator_locations')
    op.drop_column('services','destination_lng')
    op.drop_column('services','destination_lat')
