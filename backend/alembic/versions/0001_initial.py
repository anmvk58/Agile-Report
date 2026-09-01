"""initial schema"""
from alembic import op
import sqlalchemy as sa
revision="0001_initial"; down_revision=None; branch_labels=None; depends_on=None
def upgrade():
    from app.db.base import Base
    from app.models.entities import User, UserStory, UserStoryAssignment, DailyReport, DailyReportItem, WeeklyReport, Setting
    bind=op.get_bind(); Base.metadata.create_all(bind=bind)
def downgrade():
    from app.db.base import Base
    Base.metadata.drop_all(bind=op.get_bind())

