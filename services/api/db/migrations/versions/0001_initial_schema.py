"""Initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-09-20 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Cameras
    op.create_table('cameras',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('source_uri', sa.String(), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('zone', sa.String(length=100), nullable=True),
        sa.Column('priority', sa.Integer(), server_default='1', nullable=True),
        sa.Column('enabled', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('status', sa.String(length=20), server_default='OFFLINE', nullable=True),
        sa.Column('last_frame_ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Fences
    op.create_table('fences',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('camera_id', sa.String(length=50), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('polygon', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('direction', sa.String(length=20), server_default='BOTH', nullable=True),
        sa.Column('debounce_frames', sa.Integer(), server_default='3', nullable=True),
        sa.Column('enabled', sa.Boolean(), server_default='true', nullable=True),
        sa.ForeignKeyConstraint(['camera_id'], ['cameras.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Tracks
    op.create_table('tracks',
        sa.Column('track_id', sa.String(length=50), nullable=False),
        sa.Column('camera_id', sa.String(length=50), nullable=True),
        sa.Column('class_name', sa.String(length=50), nullable=False),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('trajectory', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(['camera_id'], ['cameras.id'], ),
        sa.PrimaryKeyConstraint('track_id')
    )

    # 4. Events
    op.create_table('events',
        sa.Column('event_id', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('camera_id', sa.String(length=50), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('track_id', sa.String(length=50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('severity', sa.String(length=20), server_default='INFO', nullable=True),
        sa.Column('media_ref', sa.String(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['camera_id'], ['cameras.id'], ),
        sa.PrimaryKeyConstraint('event_id', 'timestamp')
    )
    op.create_index(op.f('ix_events_camera_id'), 'events', ['camera_id'], unique=False)
    op.create_index(op.f('ix_events_severity'), 'events', ['severity'], unique=False)
    op.create_index(op.f('ix_events_timestamp'), 'events', ['timestamp'], unique=False)
    op.create_index(op.f('ix_events_type'), 'events', ['type'], unique=False)



    # 5. WatchlistEntries
    op.create_table('watchlist_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=False),
        sa.Column('reference', sa.String(), nullable=True),
        sa.Column('enabled', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('threshold', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. PlateReads
    op.create_table('plate_reads',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(length=100), nullable=True),
        sa.Column('plate_text', sa.String(length=50), nullable=False),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('format_valid', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('watchlist_hit', sa.Boolean(), server_default='false', nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 7. CameraHealth
    op.create_table('camera_health',
        sa.Column('camera_id', sa.String(length=50), nullable=False),
        sa.Column('last_frame_ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('fps', sa.Float(), nullable=True),
        sa.Column('error_count', sa.Integer(), server_default='0', nullable=True),
        sa.ForeignKeyConstraint(['camera_id'], ['cameras.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('camera_id')
    )

    # 8. AuditLog
    op.create_table('audit_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('actor', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('audit_log')
    op.drop_table('camera_health')
    op.drop_table('plate_reads')
    op.drop_table('watchlist_entries')
    op.drop_index(op.f('ix_events_type'), table_name='events')
    op.drop_index(op.f('ix_events_timestamp'), table_name='events')
    op.drop_index(op.f('ix_events_severity'), table_name='events')
    op.drop_index(op.f('ix_events_camera_id'), table_name='events')
    op.drop_table('events')
    op.drop_table('tracks')
    op.drop_table('fences')
    op.drop_table('cameras')
