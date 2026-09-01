import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from app.core.config import settings
from app.core.security import create_token, get_current_user, hash_password, require_admin, verify_password
from app.db.base import get_db, utcnow
from app.models.entities import DailyReport, DailyReportItem, DailyReportReopenAudit, DailyStatus, Priority, Role, Setting, StoryStatus, User, UserStory, UserStoryAssignment, WeeklyReport, WeeklyStatus
from app.schemas.api import *
from app.schemas.common import Message, Page
from app.services.daily import get_report, serialize_report, upsert_report
from app.services.weekly import aggregate_week, csv_bytes, markdown

router=APIRouter(prefix="/api")
def local_today(): return datetime.now(ZoneInfo(settings.timezone)).date()
def commit_or_conflict(db):
    try: db.commit()
    except IntegrityError as exc: db.rollback(); raise HTTPException(409,"Dữ liệu bị trùng hoặc đang được tham chiếu") from exc
def story_out(story:UserStory):
    data=StoryOut.model_validate(story).model_dump(); data["assignees"]=[UserOut.model_validate(a.user) for a in story.assignments]; return data

@router.post("/auth/login",response_model=TokenResponse)
def login(body:LoginRequest,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.username==body.username))
    if not user or not verify_password(body.password,user.password_hash): raise HTTPException(401,"Tên đăng nhập hoặc mật khẩu không đúng")
    if not user.is_active: raise HTTPException(403,"Tài khoản đã bị khóa")
    return TokenResponse(access_token=create_token(user))
@router.get("/auth/me",response_model=UserOut)
def me(user:User=Depends(get_current_user)): return user
@router.post("/auth/change-password",response_model=Message)
def change_password(body:ChangePassword,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if not verify_password(body.current_password,user.password_hash): raise HTTPException(422,"Mật khẩu hiện tại không đúng")
    user.password_hash=hash_password(body.new_password); db.commit(); return Message(message="Đổi mật khẩu thành công")

@router.get("/users",response_model=Page[UserOut])
def users(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),search:str|None=None,_=Depends(require_admin),db:Session=Depends(get_db)):
    q=select(User); count=select(func.count()).select_from(User)
    if search: cond=or_(User.username.contains(search),User.full_name.contains(search),User.email.contains(search)); q=q.where(cond); count=count.where(cond)
    total=db.scalar(count) or 0; items=db.scalars(q.order_by(User.full_name).offset((page-1)*page_size).limit(page_size)).all()
    return Page(items=items,total=total,page=page,page_size=page_size)
@router.post("/users",response_model=UserOut,status_code=201)
def create_user(body:UserCreate,_=Depends(require_admin),db:Session=Depends(get_db)):
    user=User(**body.model_dump(exclude={"password"}),password_hash=hash_password(body.password)); db.add(user); commit_or_conflict(db); db.refresh(user); return user
@router.get("/users/{user_id}",response_model=UserOut)
def get_user(user_id:int,_=Depends(require_admin),db:Session=Depends(get_db)):
    user=db.get(User,user_id)
    if not user: raise HTTPException(404,"Không tìm thấy thành viên")
    return user
@router.patch("/users/{user_id}",response_model=UserOut)
def update_user(user_id:int,body:UserUpdate,_=Depends(require_admin),db:Session=Depends(get_db)):
    user=db.get(User,user_id)
    if not user: raise HTTPException(404,"Không tìm thấy thành viên")
    for k,v in body.model_dump(exclude_unset=True).items(): setattr(user,k,v)
    commit_or_conflict(db); return user
@router.post("/users/{user_id}/reset-password",response_model=Message)
def reset_password(user_id:int,body:PasswordReset,_=Depends(require_admin),db:Session=Depends(get_db)):
    user=db.get(User,user_id)
    if not user: raise HTTPException(404,"Không tìm thấy thành viên")
    user.password_hash=hash_password(body.new_password); db.commit(); return Message(message="Đã đặt lại mật khẩu")
@router.patch("/users/{user_id}/status",response_model=UserOut)
def set_status(user_id:int,body:StatusUpdate,admin:User=Depends(require_admin),db:Session=Depends(get_db)):
    user=db.get(User,user_id)
    if not user: raise HTTPException(404,"Không tìm thấy thành viên")
    if user.id==admin.id and not body.is_active: raise HTTPException(422,"Admin không thể tự khóa chính mình")
    user.is_active=body.is_active; db.commit(); return user

@router.get("/user-stories")
def stories(page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=100),search:str|None=None,story_status:StoryStatus|None=None,priority:Priority|None=None,assignee_id:int|None=None,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    q=select(UserStory).options(selectinload(UserStory.assignments).selectinload(UserStoryAssignment.user))
    if user.role==Role.MEMBER: q=q.where(UserStory.status!=StoryStatus.CLOSED)
    if search: q=q.where(or_(UserStory.code.contains(search),UserStory.title.contains(search)))
    if story_status:q=q.where(UserStory.status==story_status)
    if priority:q=q.where(UserStory.priority==priority)
    if assignee_id:q=q.join(UserStoryAssignment).where(UserStoryAssignment.user_id==assignee_id)
    all_items=db.scalars(q.order_by(UserStory.updated_at.desc())).unique().all(); sliced=all_items[(page-1)*page_size:page*page_size]
    return {"items":[story_out(x) for x in sliced],"total":len(all_items),"page":page,"page_size":page_size}
@router.post("/user-stories",status_code=201)
def create_story(body:StoryCreate,admin:User=Depends(require_admin),db:Session=Depends(get_db)):
    story=UserStory(**body.model_dump(exclude={"assignee_ids"}),created_by=admin.id); db.add(story); db.flush()
    story.assignments=[UserStoryAssignment(user_id=x) for x in set(body.assignee_ids)]; commit_or_conflict(db)
    return story_out(db.scalar(select(UserStory).where(UserStory.id==story.id).options(selectinload(UserStory.assignments).selectinload(UserStoryAssignment.user))))
@router.get("/user-stories/{story_id}")
def get_story(story_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    story=db.scalar(select(UserStory).where(UserStory.id==story_id).options(selectinload(UserStory.assignments).selectinload(UserStoryAssignment.user)))
    if not story: raise HTTPException(404,"Không tìm thấy User Story")
    if user.role==Role.MEMBER and story.status==StoryStatus.CLOSED: raise HTTPException(403,"User Story đã đóng không còn khả dụng")
    return story_out(story)
@router.patch("/user-stories/{story_id}")
def update_story(story_id:int,body:StoryUpdate,_=Depends(require_admin),db:Session=Depends(get_db)):
    story=db.scalar(select(UserStory).where(UserStory.id==story_id).options(selectinload(UserStory.assignments).selectinload(UserStoryAssignment.user)))
    if not story: raise HTTPException(404,"Không tìm thấy User Story")
    values=body.model_dump(exclude_unset=True); assignees=values.pop("assignee_ids",None)
    next_start=values.get("start_date",story.start_date); next_due=values.get("due_date",story.due_date)
    if next_start and next_due and next_due<next_start: raise HTTPException(422,"Hạn hoàn thành không được trước ngày bắt đầu")
    for k,v in values.items(): setattr(story,k,v)
    if body.status==StoryStatus.CLOSED: story.closed_at=utcnow()
    elif body.status is not None: story.closed_at=None
    if assignees is not None: story.assignments=[UserStoryAssignment(user_id=x) for x in set(assignees)]
    commit_or_conflict(db); return story_out(story)
@router.delete("/user-stories/{story_id}",status_code=204)
def delete_story(story_id:int,_=Depends(require_admin),db:Session=Depends(get_db)):
    story=db.scalar(select(UserStory).where(UserStory.id==story_id).options(selectinload(UserStory.assignments)))
    if not story: raise HTTPException(404,"Không tìm thấy User Story")
    linked_items=db.scalar(select(func.count()).select_from(DailyReportItem).where(DailyReportItem.user_story_id==story_id)) or 0
    if linked_items: raise HTTPException(409,"User Story đã có lịch sử Daily. Hãy chuyển sang trạng thái Đã đóng thay vì xóa")
    db.delete(story); db.commit(); return Response(status_code=204)
@router.get("/user-stories/{story_id}/timeline")
def story_timeline(story_id:int,_=Depends(require_admin),db:Session=Depends(get_db)):
    if not db.get(UserStory,story_id): raise HTTPException(404,"Không tìm thấy User Story")
    rows=db.execute(select(DailyReport.report_date,User.full_name,DailyReportItem).join(DailyReportItem).join(User).where(DailyReportItem.user_story_id==story_id).order_by(DailyReport.report_date.desc())).all()
    return [{"date":d,"member":name,"task_title":i.task_title,"progress_percent":i.progress_percent,"has_issue":i.has_issue,"issue_description":i.issue_description} for d,name,i in rows]

@router.get("/daily-reports/me")
def my_history(date_from:date|None=None,date_to:date|None=None,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    q=select(DailyReport).where(DailyReport.user_id==user.id).options(selectinload(DailyReport.items).selectinload(DailyReportItem.user_story),selectinload(DailyReport.user))
    if date_from:q=q.where(DailyReport.report_date>=date_from)
    if date_to:q=q.where(DailyReport.report_date<=date_to)
    return [serialize_report(r) for r in db.scalars(q.order_by(DailyReport.report_date.desc())).all()]
@router.get("/daily-reports/me/{report_date}")
def my_daily(report_date:date,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    report=get_report(db,user.id,report_date)
    if not report: raise HTTPException(404,"Chưa có Daily cho ngày này")
    return serialize_report(report)
@router.put("/daily-reports/me/{report_date}")
def save_daily(report_date:date,body:DailyUpsert,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    report=get_report(db,user.id,report_date)
    if report_date<local_today() and not (report and report.status==DailyStatus.DRAFT and report.is_reopened):
        raise HTTPException(409,"Daily quá khứ đã khóa. Vui lòng liên hệ Admin để mở lại")
    return serialize_report(upsert_report(db,user.id,report_date,body))
@router.post("/daily-reports/me/{report_date}/submit")
def submit_daily(report_date:date,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if report_date>local_today(): raise HTTPException(422,"Không thể submit Daily của ngày tương lai")
    report=get_report(db,user.id,report_date)
    if not report: raise HTTPException(404,"Hãy lưu Daily trước khi submit")
    if report_date<local_today() and not (report.status==DailyStatus.DRAFT and report.is_reopened):
        raise HTTPException(409,"Daily quá khứ đã khóa. Vui lòng liên hệ Admin để mở lại")
    report.status=DailyStatus.SUBMITTED; report.submitted_at=utcnow(); report.is_reopened=False; db.commit(); return serialize_report(get_report(db,user.id,report_date))

@router.get("/admin/daily-reports")
def team_daily(report_date:date|None=None,date_from:date|None=None,date_to:date|None=None,issues_only:bool=False,_=Depends(require_admin),db:Session=Depends(get_db)):
    start=date_from or report_date or local_today()
    end=date_to or report_date or start
    if end<start: raise HTTPException(422,"Ngày kết thúc phải sau hoặc bằng ngày bắt đầu")
    members=db.scalars(select(User).where(User.is_active.is_(True),User.role==Role.MEMBER).order_by(User.full_name)).all()
    reports=db.scalars(select(DailyReport).where(DailyReport.report_date.between(start,end)).options(selectinload(DailyReport.items).selectinload(DailyReportItem.user_story),selectinload(DailyReport.user))).all()
    by_date_user={(r.report_date,r.user_id):r for r in reports}
    rows=[]
    current=start
    while current<=end:
        for member in members:
            report=by_date_user.get((current,member.id))
            if issues_only and (not report or not any(item.has_issue for item in report.items)): continue
            rows.append({"report_date":current,"user":UserOut.model_validate(member),"report":serialize_report(report) if report else None})
        current+=timedelta(days=1)
    return rows
@router.get("/admin/daily-reports/{report_id}")
def admin_daily(report_id:int,_=Depends(require_admin),db:Session=Depends(get_db)):
    report=db.scalar(select(DailyReport).where(DailyReport.id==report_id).options(selectinload(DailyReport.items).selectinload(DailyReportItem.user_story),selectinload(DailyReport.user)))
    if not report: raise HTTPException(404,"Không tìm thấy Daily")
    return serialize_report(report)
@router.get("/admin/daily-reports/{report_id}/reopen-history")
def daily_reopen_history(report_id:int,_=Depends(require_admin),db:Session=Depends(get_db)):
    if not db.get(DailyReport,report_id): raise HTTPException(404,"Không tìm thấy Daily")
    rows=db.scalars(select(DailyReportReopenAudit).where(DailyReportReopenAudit.daily_report_id==report_id).options(selectinload(DailyReportReopenAudit.admin)).order_by(DailyReportReopenAudit.reopened_at.desc())).all()
    return [{"id":row.id,"reason":row.reason,"reopened_at":row.reopened_at,"reopened_by":row.reopened_by,"reopened_by_name":row.admin.full_name} for row in rows]
@router.post("/admin/daily-reports/{report_id}/reopen")
def reopen_daily(report_id:int,body:DailyReopenRequest,admin:User=Depends(require_admin),db:Session=Depends(get_db)):
    report=db.get(DailyReport,report_id)
    if not report: raise HTTPException(404,"Không tìm thấy Daily")
    if report.report_date>=local_today(): raise HTTPException(422,"Chỉ cần mở lại Daily của ngày đã qua")
    if report.is_reopened: raise HTTPException(409,"Daily này đang được mở để chỉnh sửa")
    reason=body.reason.strip()
    if len(reason)<3: raise HTTPException(422,"Lý do mở lại phải có ít nhất 3 ký tự")
    report.status=DailyStatus.DRAFT; report.is_reopened=True
    db.add(DailyReportReopenAudit(daily_report_id=report.id,reopened_by=admin.id,reason=reason))
    db.commit()
    return serialize_report(get_report(db,report.user_id,report.report_date))
@router.patch("/admin/daily-reports/{report_id}")
def admin_update_daily(report_id:int,body:DailyUpsert,_=Depends(require_admin),db:Session=Depends(get_db)):
    report=db.get(DailyReport,report_id)
    if not report: raise HTTPException(404,"Không tìm thấy Daily")
    return serialize_report(upsert_report(db,report.user_id,report.report_date,body))
@router.delete("/admin/daily-reports/{report_id}",status_code=204)
def delete_daily(report_id:int,_=Depends(require_admin),db:Session=Depends(get_db)):
    report=db.get(DailyReport,report_id)
    if not report: raise HTTPException(404,"Không tìm thấy Daily")
    db.delete(report); db.commit(); return Response(status_code=204)

@router.get("/dashboard/summary")
def dashboard(_=Depends(require_admin),db:Session=Depends(get_db)):
    today=local_today(); members=db.scalars(select(User).where(User.role==Role.MEMBER,User.is_active.is_(True))).all()
    submitted_ids=set(db.scalars(select(DailyReport.user_id).where(DailyReport.report_date==today,DailyReport.status==DailyStatus.SUBMITTED)).all())
    active_stories=db.scalar(select(func.count()).select_from(UserStory).where(UserStory.status==StoryStatus.IN_PROGRESS)) or 0
    blocked_stories=db.scalar(select(func.count()).select_from(UserStory).where(UserStory.status==StoryStatus.BLOCKED)) or 0
    issues=db.scalar(select(func.count()).select_from(DailyReportItem).join(DailyReport).where(DailyReport.report_date==today,DailyReportItem.has_issue.is_(True))) or 0
    week_start=today-timedelta(days=today.weekday())
    week_counts=db.execute(select(DailyReport.report_date,func.count()).where(DailyReport.report_date.between(week_start,today),DailyReport.status==DailyStatus.SUBMITTED).group_by(DailyReport.report_date)).all()
    return {"active_members":len(members),"submitted_today":len(submitted_ids),"missing_today":len(members)-len(submitted_ids),"active_stories":active_stories,"blocked_stories":blocked_stories,"issues_today":issues,"missing_members":[UserOut.model_validate(m) for m in members if m.id not in submitted_ids],"week_progress":[{"date":d,"submitted":c,"total":len(members)} for d,c in week_counts]}
@router.get("/dashboard/blockers")
def blockers(limit:int=Query(10,ge=1,le=50),_=Depends(require_admin),db:Session=Depends(get_db)):
    rows=db.execute(
        select(DailyReport.report_date,User.full_name,DailyReportItem,UserStory)
        .select_from(DailyReportItem)
        .join(DailyReport,DailyReportItem.daily_report_id==DailyReport.id)
        .join(User,DailyReport.user_id==User.id)
        .outerjoin(UserStory,DailyReportItem.user_story_id==UserStory.id)
        .where(DailyReportItem.has_issue.is_(True))
        .order_by(DailyReport.report_date.desc())
        .limit(limit)
    ).all()
    return [{"date":d,"member":name,"task_title":i.task_title,"issue":i.issue_description,"story_code":s.code if s else None} for d,name,i,s in rows]
@router.get("/dashboard/overdue-stories")
def overdue(_=Depends(require_admin),db:Session=Depends(get_db)):
    stories=db.scalars(select(UserStory).where(UserStory.due_date<local_today(),UserStory.status.not_in([StoryStatus.DONE,StoryStatus.CLOSED])).order_by(UserStory.due_date)).all()
    return [{"id":s.id,"code":s.code,"title":s.title,"due_date":s.due_date,"status":s.status,"progress_percent":s.progress_percent} for s in stories]

@router.post("/weekly-reports/preview")
def preview_week(body:WeeklyRange,_=Depends(require_admin),db:Session=Depends(get_db)): return aggregate_week(db,body.week_start,body.week_end,body.include_next_plans)
@router.post("/weekly-reports/generate",status_code=201)
def generate_week(body:WeeklyRange,admin:User=Depends(require_admin),db:Session=Depends(get_db)):
    snapshot=aggregate_week(db,body.week_start,body.week_end,body.include_next_plans)
    report=WeeklyReport(week_start=body.week_start,week_end=body.week_end,generated_by=admin.id,snapshot_data=json.dumps(snapshot,ensure_ascii=False)); db.add(report); db.commit(); db.refresh(report)
    return {"id":report.id,"week_start":report.week_start,"week_end":report.week_end,"generated_by":report.generated_by,"generated_at":report.generated_at,"status":report.status,"snapshot":snapshot}
@router.get("/weekly-reports")
def weekly_list(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),_=Depends(require_admin),db:Session=Depends(get_db)):
    total=db.scalar(select(func.count()).select_from(WeeklyReport)) or 0; rows=db.scalars(select(WeeklyReport).order_by(WeeklyReport.generated_at.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {"items":[{"id":r.id,"week_start":r.week_start,"week_end":r.week_end,"generated_by":r.generated_by,"generated_at":r.generated_at,"status":r.status,"snapshot":json.loads(r.snapshot_data)} for r in rows],"total":total,"page":page,"page_size":page_size}
@router.get("/weekly-reports/{report_id}")
def weekly_get(report_id:int,_=Depends(require_admin),db:Session=Depends(get_db)):
    r=db.get(WeeklyReport,report_id)
    if not r: raise HTTPException(404,"Không tìm thấy báo cáo tuần")
    return {"id":r.id,"week_start":r.week_start,"week_end":r.week_end,"generated_by":r.generated_by,"generated_at":r.generated_at,"status":r.status,"snapshot":json.loads(r.snapshot_data)}
@router.post("/weekly-reports/{report_id}/finalize")
def finalize_week(report_id:int,_=Depends(require_admin),db:Session=Depends(get_db)):
    r=db.get(WeeklyReport,report_id)
    if not r: raise HTTPException(404,"Không tìm thấy báo cáo tuần")
    r.status=WeeklyStatus.FINALIZED; db.commit(); return weekly_get(report_id,_,db)
@router.get("/weekly-reports/{report_id}/export")
def export_week(report_id:int,format:str=Query(pattern="^(markdown|csv)$"),_=Depends(require_admin),db:Session=Depends(get_db)):
    r=db.get(WeeklyReport,report_id)
    if not r: raise HTTPException(404,"Không tìm thấy báo cáo tuần")
    snapshot=json.loads(r.snapshot_data)
    if format=="markdown":
        return Response(markdown(snapshot),media_type="text/markdown; charset=utf-8",headers={"Content-Disposition":f'attachment; filename="weekly-{r.week_start}.md"'})
    return StreamingResponse(iter([csv_bytes(snapshot)]),media_type="text/csv; charset=utf-8",headers={"Content-Disposition":f'attachment; filename="weekly-{r.week_start}.csv"'})

@router.get("/settings/workdays")
def get_workdays(_=Depends(require_admin),db:Session=Depends(get_db)):
    row=db.scalar(select(Setting).where(Setting.setting_key=="workdays")); return {"workdays":json.loads(row.setting_value) if row else [0,1,2,3,4]}
@router.patch("/settings/workdays")
def update_workdays(body:dict,_=Depends(require_admin),db:Session=Depends(get_db)):
    days=body.get("workdays")
    if not isinstance(days,list) or not days or any(not isinstance(x,int) or x<0 or x>6 for x in days): raise HTTPException(422,"Danh sách ngày làm việc không hợp lệ")
    row=db.scalar(select(Setting).where(Setting.setting_key=="workdays"))
    if not row: row=Setting(setting_key="workdays",setting_value="[]",description="Ngày làm việc trong tuần"); db.add(row)
    row.setting_value=json.dumps(sorted(set(days))); db.commit(); return {"workdays":json.loads(row.setting_value)}
