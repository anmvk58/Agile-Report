import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import SessionLocal, utcnow
from app.models.entities import DailyReport, DailyReportItem, DailyStatus, Priority, Role, Setting, StoryStatus, User, UserStory, UserStoryAssignment

def run():
    db=SessionLocal()
    try:
        if db.scalar(select(User.id).limit(1)): return
        admin=User(username="admin",full_name="Quản trị hệ thống",email="admin@example.com",password_hash=hash_password(settings.admin_initial_password),role=Role.ADMIN)
        db.add(admin); db.flush()
        members=[]
        names=[("an.nguyen","Nguyễn Minh An"),("binh.tran","Trần Gia Bình"),("chi.le","Lê Mai Chi"),("dung.pham","Phạm Hoàng Dũng"),("ha.vo","Võ Thanh Hà"),("khanh.do","Đỗ Quốc Khánh")]
        for idx,(username,name) in enumerate(names,1): members.append(User(username=username,full_name=name,email=f"member{idx}@example.com",password_hash=hash_password("Member123!"),role=Role.MEMBER))
        db.add_all(members); db.flush()
        today=datetime.now(ZoneInfo(settings.timezone)).date()
        specs=[("US-001","Đăng nhập và phân quyền",StoryStatus.DONE,Priority.HIGH,100),("US-002","Form Daily tối ưu",StoryStatus.IN_PROGRESS,Priority.CRITICAL,70),("US-003","Dashboard quản trị",StoryStatus.IN_PROGRESS,Priority.HIGH,45),("US-004","Báo cáo tuần",StoryStatus.BLOCKED,Priority.HIGH,30),("US-005","Chuẩn hóa tài liệu",StoryStatus.TODO,Priority.MEDIUM,0)]
        stories=[]
        for i,(code,title,story_status,priority,progress) in enumerate(specs):
            story=UserStory(code=code,title=title,description=f"Mô tả cho {title}",status=story_status,priority=priority,start_date=today-timedelta(days=14),due_date=today+timedelta(days=5-i*2),progress_percent=progress,created_by=admin.id)
            story.assignments=[UserStoryAssignment(user_id=m.id) for m in members[i%3:(i%3)+3]]; stories.append(story)
        db.add_all(stories); db.flush()
        for offset in range(13,-1,-1):
            day=today-timedelta(days=offset)
            if day.weekday()>=5: continue
            for idx,m in enumerate(members):
                if (offset+idx)%6==0: continue
                story=stories[idx%len(stories)]; issue=story.status==StoryStatus.BLOCKED and offset<5
                report=DailyReport(user_id=m.id,report_date=day,status=DailyStatus.SUBMITTED,submitted_at=utcnow(),general_note="Daily mẫu được tạo tự động")
                report.items=[DailyReportItem(user_story_id=story.id,task_title=f"Hoàn thiện phần việc {story.code}",yesterday_work="Đã hoàn thành phần phân tích và triển khai chính",today_plan="Tiếp tục kiểm thử và xử lý phản hồi",has_issue=issue,issue_description="Đang chờ xác nhận nghiệp vụ từ bên liên quan" if issue else None,progress_percent=max(0,min(100,story.progress_percent+random.randint(-10,10))))]
                db.add(report)
        db.add(Setting(setting_key="workdays",setting_value="[0,1,2,3,4]",description="Ngày làm việc: Thứ Hai đến Thứ Sáu")); db.commit()
    finally: db.close()

if __name__=="__main__": run()
