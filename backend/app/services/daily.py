from datetime import date
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.models.entities import DailyReport, DailyReportItem, StoryStatus, UserStory, utcnow
from app.schemas.api import DailyUpsert

def get_report(db:Session,user_id:int,report_date:date):
    return db.scalar(select(DailyReport).where(DailyReport.user_id==user_id,DailyReport.report_date==report_date).options(selectinload(DailyReport.items).selectinload(DailyReportItem.user_story),selectinload(DailyReport.user)))
def validate_story(db:Session,_user_id:int,story_id:int|None,existing_story_id:int|None=None):
    if story_id is None:return
    story=db.get(UserStory,story_id)
    if not story: raise HTTPException(404,"Không tìm thấy User Story")
    if story.status==StoryStatus.CLOSED and story_id!=existing_story_id: raise HTTPException(422,"Không thể chọn User Story đã đóng")
def upsert_report(db:Session,user_id:int,report_date:date,data:DailyUpsert):
    report=get_report(db,user_id,report_date)
    old_ids={i.id:i.user_story_id for i in report.items} if report else {}
    for item in data.items: validate_story(db,user_id,item.user_story_id,old_ids.get(item.id))
    if not report:
        report=DailyReport(user_id=user_id,report_date=report_date)
        db.add(report); db.flush()
    report.general_note=data.general_note
    report.items.clear(); db.flush()
    for item in data.items:
        report.items.append(DailyReportItem(**item.model_dump(exclude={"id"})))
    db.commit()
    return get_report(db,user_id,report_date)
def serialize_report(report:DailyReport)->dict:
    return {"id":report.id,"user_id":report.user_id,"report_date":report.report_date,"general_note":report.general_note,"status":report.status,"submitted_at":report.submitted_at,"is_reopened":report.is_reopened,"created_at":report.created_at,"updated_at":report.updated_at,"user":report.user,"items":[{"id":i.id,"user_story_id":i.user_story_id,"story_code":i.user_story.code if i.user_story else None,"story_title":i.user_story.title if i.user_story else None,"task_title":i.task_title,"yesterday_work":i.yesterday_work,"today_plan":i.today_plan,"has_issue":i.has_issue,"issue_description":i.issue_description,"progress_percent":i.progress_percent,"created_at":i.created_at,"updated_at":i.updated_at} for i in report.items]}
