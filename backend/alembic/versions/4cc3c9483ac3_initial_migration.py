"""Full schema migration — all tables

Revision ID: 4cc3c9483ac3
Revises: 
Create Date: 2026-07-11 01:55:06.863714

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4cc3c9483ac3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables matching the ORM models using raw SQL to avoid enum conflicts."""
    conn = op.get_bind()

    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_status') THEN
                CREATE TYPE user_status AS ENUM ('active', 'inactive', 'suspended', 'admin');
            END IF;
        END $$;

        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'theme_preference') THEN
                CREATE TYPE theme_preference AS ENUM ('light', 'dark', 'system');
            END IF;
        END $$;

        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'meeting_type') THEN
                CREATE TYPE meeting_type AS ENUM ('instant', 'scheduled', 'recurring', 'webinar');
            END IF;
        END $$;

        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'meeting_status') THEN
                CREATE TYPE meeting_status AS ENUM ('scheduled', 'active', 'ended', 'cancelled');
            END IF;
        END $$;

        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'participant_role') THEN
                CREATE TYPE participant_role AS ENUM ('host', 'co_host', 'presenter', 'attendee');
            END IF;
        END $$;

        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'connection_status') THEN
                CREATE TYPE connection_status AS ENUM ('connecting', 'connected', 'reconnecting', 'disconnected');
            END IF;
        END $$;

        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'recording_status') THEN
                CREATE TYPE recording_status AS ENUM ('recording', 'processing', 'ready', 'failed');
            END IF;
        END $$;

        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notification_type') THEN
                CREATE TYPE notification_type AS ENUM (
                    'meeting_invite', 'meeting_started', 'meeting_ended',
                    'meeting_reminder', 'recording_ready', 'system', 'chat_mention'
                );
            END IF;
        END $$;

        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'invitation_status') THEN
                CREATE TYPE invitation_status AS ENUM ('pending', 'accepted', 'declined', 'cancelled');
            END IF;
        END $$;

        CREATE TABLE IF NOT EXISTS users (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at      TIMESTAMPTZ,
            is_deleted      BOOLEAN NOT NULL DEFAULT FALSE,
            created_by      UUID,
            updated_by      UUID,
            email           VARCHAR(255) NOT NULL,
            username        VARCHAR(50),
            password_hash   VARCHAR(255),
            first_name      VARCHAR(100) NOT NULL,
            last_name       VARCHAR(100) NOT NULL,
            avatar          VARCHAR(500),
            bio             TEXT,
            timezone        VARCHAR(100) NOT NULL DEFAULT 'UTC',
            language        VARCHAR(10) NOT NULL DEFAULT 'en',
            theme           theme_preference NOT NULL DEFAULT 'system',
            status          user_status NOT NULL DEFAULT 'active',
            email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
            last_login      TIMESTAMPTZ,
            email_verify_token    VARCHAR(255),
            password_reset_token  VARCHAR(255)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email);
        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users(username) WHERE username IS NOT NULL;
        CREATE INDEX IF NOT EXISTS ix_users_is_deleted ON users(is_deleted);
        CREATE INDEX IF NOT EXISTS ix_users_created_at ON users(created_at);
        CREATE INDEX IF NOT EXISTS ix_users_email_verified ON users(email, email_verified);
        CREATE INDEX IF NOT EXISTS ix_users_status_created ON users(status, created_at);
        CREATE INDEX IF NOT EXISTS ix_users_email_verify_token ON users(email_verify_token) WHERE email_verify_token IS NOT NULL;
        CREATE INDEX IF NOT EXISTS ix_users_password_reset_token ON users(password_reset_token) WHERE password_reset_token IS NOT NULL;

        CREATE TABLE IF NOT EXISTS sessions (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at          TIMESTAMPTZ,
            is_deleted          BOOLEAN NOT NULL DEFAULT FALSE,
            created_by          UUID,
            updated_by          UUID,
            user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            refresh_token_hash  VARCHAR(255) NOT NULL,
            expires_at          TIMESTAMPTZ NOT NULL,
            user_agent          VARCHAR(500),
            ip_address          VARCHAR(45)
        );
        CREATE INDEX IF NOT EXISTS ix_sessions_user_id ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS ix_sessions_is_deleted ON sessions(is_deleted);

        CREATE TABLE IF NOT EXISTS meetings (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at          TIMESTAMPTZ,
            is_deleted          BOOLEAN NOT NULL DEFAULT FALSE,
            created_by          UUID,
            updated_by          UUID,
            host_id             UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            title               VARCHAR(255) NOT NULL,
            description         TEXT,
            meeting_code        VARCHAR(20) NOT NULL,
            meeting_password    VARCHAR(255),
            scheduled_start     TIMESTAMPTZ,
            scheduled_end       TIMESTAMPTZ,
            actual_start        TIMESTAMPTZ,
            actual_end          TIMESTAMPTZ,
            meeting_type        meeting_type NOT NULL DEFAULT 'instant',
            status              meeting_status NOT NULL DEFAULT 'scheduled',
            recording_enabled   BOOLEAN NOT NULL DEFAULT FALSE,
            waiting_room        BOOLEAN NOT NULL DEFAULT FALSE,
            locked              BOOLEAN NOT NULL DEFAULT FALSE
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ix_meetings_meeting_code ON meetings(meeting_code);
        CREATE INDEX IF NOT EXISTS ix_meetings_host_id ON meetings(host_id);
        CREATE INDEX IF NOT EXISTS ix_meetings_status ON meetings(status);
        CREATE INDEX IF NOT EXISTS ix_meetings_is_deleted ON meetings(is_deleted);
        CREATE INDEX IF NOT EXISTS ix_meetings_created_at ON meetings(created_at);
        CREATE INDEX IF NOT EXISTS ix_meetings_host_status ON meetings(host_id, status);
        CREATE INDEX IF NOT EXISTS ix_meetings_code_status ON meetings(meeting_code, status);
        CREATE INDEX IF NOT EXISTS ix_meetings_scheduled_start ON meetings(scheduled_start);

        CREATE TABLE IF NOT EXISTS meeting_settings (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at          TIMESTAMPTZ,
            is_deleted          BOOLEAN NOT NULL DEFAULT FALSE,
            created_by          UUID,
            updated_by          UUID,
            meeting_id          UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            allow_chat          BOOLEAN NOT NULL DEFAULT TRUE,
            allow_screen_share  BOOLEAN NOT NULL DEFAULT TRUE,
            allow_recording     BOOLEAN NOT NULL DEFAULT TRUE,
            allow_unmute        BOOLEAN NOT NULL DEFAULT TRUE,
            allow_camera        BOOLEAN NOT NULL DEFAULT TRUE,
            waiting_room        BOOLEAN NOT NULL DEFAULT FALSE,
            allow_reactions     BOOLEAN NOT NULL DEFAULT TRUE,
            allow_polls         BOOLEAN NOT NULL DEFAULT TRUE,
            allow_hand_raise    BOOLEAN NOT NULL DEFAULT TRUE,
            mute_on_entry       BOOLEAN NOT NULL DEFAULT FALSE,
            video_off_on_entry  BOOLEAN NOT NULL DEFAULT FALSE
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ix_meeting_settings_meeting_id ON meeting_settings(meeting_id);

        CREATE TABLE IF NOT EXISTS participants (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at          TIMESTAMPTZ,
            is_deleted          BOOLEAN NOT NULL DEFAULT FALSE,
            created_by          UUID,
            updated_by          UUID,
            meeting_id          UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role                participant_role NOT NULL DEFAULT 'attendee',
            joined_at           TIMESTAMPTZ,
            left_at             TIMESTAMPTZ,
            mic_enabled         BOOLEAN NOT NULL DEFAULT FALSE,
            camera_enabled      BOOLEAN NOT NULL DEFAULT FALSE,
            screen_sharing      BOOLEAN NOT NULL DEFAULT FALSE,
            hand_raised         BOOLEAN NOT NULL DEFAULT FALSE,
            connection_status   connection_status NOT NULL DEFAULT 'connecting'
        );
        CREATE INDEX IF NOT EXISTS ix_participants_meeting_id ON participants(meeting_id);
        CREATE INDEX IF NOT EXISTS ix_participants_user_id ON participants(user_id);
        CREATE INDEX IF NOT EXISTS ix_participants_is_deleted ON participants(is_deleted);
        CREATE INDEX IF NOT EXISTS ix_participants_meeting_user ON participants(meeting_id, user_id);
        CREATE INDEX IF NOT EXISTS ix_participants_meeting_role ON participants(meeting_id, role);
        CREATE INDEX IF NOT EXISTS ix_participants_user_joined ON participants(user_id, joined_at);

        CREATE TABLE IF NOT EXISTS meeting_invitations (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at      TIMESTAMPTZ,
            is_deleted      BOOLEAN NOT NULL DEFAULT FALSE,
            created_by      UUID,
            updated_by      UUID,
            meeting_id      UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
            invited_email   VARCHAR(255),
            invited_by      UUID REFERENCES users(id) ON DELETE SET NULL,
            status          invitation_status NOT NULL DEFAULT 'pending',
            invited_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            accepted_at     TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS ix_meeting_invitations_meeting_id ON meeting_invitations(meeting_id);
        CREATE INDEX IF NOT EXISTS ix_meeting_invitations_user_id ON meeting_invitations(user_id);

        CREATE TABLE IF NOT EXISTS messages (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at  TIMESTAMPTZ,
            is_deleted  BOOLEAN NOT NULL DEFAULT FALSE,
            created_by  UUID,
            updated_by  UUID,
            meeting_id  UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            sender_id   UUID REFERENCES users(id) ON DELETE SET NULL,
            message     TEXT NOT NULL,
            reply_to    UUID REFERENCES messages(id) ON DELETE SET NULL,
            edited      BOOLEAN NOT NULL DEFAULT FALSE,
            deleted     BOOLEAN NOT NULL DEFAULT FALSE
        );
        CREATE INDEX IF NOT EXISTS ix_messages_meeting_id ON messages(meeting_id);
        CREATE INDEX IF NOT EXISTS ix_messages_sender_id ON messages(sender_id);
        CREATE INDEX IF NOT EXISTS ix_messages_is_deleted ON messages(is_deleted);
        CREATE INDEX IF NOT EXISTS ix_messages_created_at ON messages(created_at);

        CREATE TABLE IF NOT EXISTS recordings (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at      TIMESTAMPTZ,
            is_deleted      BOOLEAN NOT NULL DEFAULT FALSE,
            created_by      UUID,
            updated_by      UUID,
            meeting_id      UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            started_by      UUID REFERENCES users(id) ON DELETE SET NULL,
            status          recording_status NOT NULL DEFAULT 'recording',
            file_url        VARCHAR(1000),
            object_key      VARCHAR(500),
            duration        INTEGER,
            size            BIGINT,
            thumbnail_url   VARCHAR(1000)
        );
        CREATE INDEX IF NOT EXISTS ix_recordings_meeting_id ON recordings(meeting_id);
        CREATE INDEX IF NOT EXISTS ix_recordings_status ON recordings(status);
        CREATE INDEX IF NOT EXISTS ix_recordings_is_deleted ON recordings(is_deleted);
        CREATE INDEX IF NOT EXISTS ix_recordings_meeting_created ON recordings(meeting_id, created_at);

        CREATE TABLE IF NOT EXISTS files (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at          TIMESTAMPTZ,
            is_deleted          BOOLEAN NOT NULL DEFAULT FALSE,
            created_by          UUID,
            updated_by          UUID,
            meeting_id          UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            uploaded_by         UUID REFERENCES users(id) ON DELETE SET NULL,
            filename            VARCHAR(255) NOT NULL,
            original_filename   VARCHAR(255) NOT NULL,
            file_url            VARCHAR(1000) NOT NULL,
            object_key          VARCHAR(500) NOT NULL,
            mime_type           VARCHAR(100) NOT NULL,
            size                BIGINT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_files_meeting_id ON files(meeting_id);
        CREATE INDEX IF NOT EXISTS ix_files_uploaded_by ON files(uploaded_by);
        CREATE INDEX IF NOT EXISTS ix_files_is_deleted ON files(is_deleted);

        CREATE TABLE IF NOT EXISTS notifications (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at  TIMESTAMPTZ,
            is_deleted  BOOLEAN NOT NULL DEFAULT FALSE,
            created_by  UUID,
            updated_by  UUID,
            user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title       VARCHAR(255) NOT NULL,
            body        TEXT NOT NULL,
            type        notification_type NOT NULL,
            read        BOOLEAN NOT NULL DEFAULT FALSE,
            action_url  VARCHAR(500),
            entity_id   UUID
        );
        CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id);
        CREATE INDEX IF NOT EXISTS ix_notifications_type ON notifications(type);
        CREATE INDEX IF NOT EXISTS ix_notifications_is_deleted ON notifications(is_deleted);
        CREATE INDEX IF NOT EXISTS ix_notifications_user_read ON notifications(user_id, read);
        CREATE INDEX IF NOT EXISTS ix_notifications_user_created ON notifications(user_id, created_at);

        CREATE TABLE IF NOT EXISTS audit_logs (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at  TIMESTAMPTZ,
            is_deleted  BOOLEAN NOT NULL DEFAULT FALSE,
            created_by  UUID,
            updated_by  UUID,
            user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
            action      VARCHAR(100) NOT NULL,
            entity      VARCHAR(100) NOT NULL,
            entity_id   UUID,
            ip          VARCHAR(45),
            device      VARCHAR(255),
            user_agent  TEXT,
            old_value   TEXT,
            new_value   TEXT,
            extra       TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_entity ON audit_logs(entity);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);
        CREATE INDEX IF NOT EXISTS ix_audit_user_created ON audit_logs(user_id, created_at);
        CREATE INDEX IF NOT EXISTS ix_audit_entity ON audit_logs(entity, entity_id);
    """))


def downgrade() -> None:
    """Drop all tables and enums."""
    conn = op.get_bind()
    conn.execute(sa.text("""
        DROP TABLE IF EXISTS audit_logs CASCADE;
        DROP TABLE IF EXISTS notifications CASCADE;
        DROP TABLE IF EXISTS files CASCADE;
        DROP TABLE IF EXISTS recordings CASCADE;
        DROP TABLE IF EXISTS messages CASCADE;
        DROP TABLE IF EXISTS meeting_invitations CASCADE;
        DROP TABLE IF EXISTS participants CASCADE;
        DROP TABLE IF EXISTS meeting_settings CASCADE;
        DROP TABLE IF EXISTS meetings CASCADE;
        DROP TABLE IF EXISTS sessions CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
        DROP TYPE IF EXISTS invitation_status;
        DROP TYPE IF EXISTS notification_type;
        DROP TYPE IF EXISTS recording_status;
        DROP TYPE IF EXISTS connection_status;
        DROP TYPE IF EXISTS participant_role;
        DROP TYPE IF EXISTS meeting_status;
        DROP TYPE IF EXISTS meeting_type;
        DROP TYPE IF EXISTS theme_preference;
        DROP TYPE IF EXISTS user_status;
    """))
