import csv, io, json
from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.models.entities import DailyReport, DailyReportItem, DailyStatus, Role, Setting, User, UserStory

def unique(values): return list(dict.fromkeys(v.strip() for v in values if v and v.strip()))
def aggregate_week(db:Session,start:date,end:date,include_next_plans:bool=True)->dict:
    reports=db.scalars(select(DailyReport).where(DailyReport.report_date.between(start,end),DailyReport.status==DailyStatus.SUBMITTED).options(selectinload(DailyReport.user),selectinload(DailyReport.items).selectinload(DailyReportItem.user_story))).all()
    setting=db.scalar(select(Setting).where(Setting.setting_key=="workdays"))
    configured=json.loads(setting.setting_value) if setting else [0,1,2,3,4]
    workdays=[start+timedelta(days=i) for i in range((end-start).days+1) if (start+timedelta(days=i)).weekday() in configured]
    active_members=db.scalars(select(User).where(User.is_active.is_(True),User.role==Role.MEMBER)).all()
    by_member=[]
    for member in active_members:
        mine=sorted([r for r in reports if r.user_id==member.id],key=lambda r:r.report_date); items=[i for r in mine for i in r.items]
        story_groups={}
        for report in mine:
            for item in report.items:
                if not item.user_story: continue
                story=story_groups.setdefault(item.user_story_id,{"story_id":item.user_story_id,"code":item.user_story.code,"title":item.user_story.title,"tasks":[]})
                story["tasks"].append({"date":report.report_date.isoformat(),"task_title":item.task_title,"completed":item.yesterday_work,"today_plan":item.today_plan,"progress_percent":item.progress_percent,"has_issue":item.has_issue,"issue_description":item.issue_description})
        by_member.append({"user_id":member.id,"full_name":member.full_name,"stories":unique([f"{i.user_story.code} — {i.user_story.title}" for i in items if i.user_story]),"story_details":list(story_groups.values()),"completed":unique([i.yesterday_work for i in items]),"in_progress":unique([i.task_title for i in items if i.progress_percent is None or i.progress_percent<100]),"next_plans":unique([i.today_plan for i in items]),"blockers":unique([i.issue_description for i in items if i.has_issue]),"submitted_days":len({r.report_date for r in mine}),"missing_days":max(0,len(workdays)-len({r.report_date for r in mine}))})
    story_ids={i.user_story_id for r in reports for i in r.items if i.user_story_id}; stories={s.id:s for s in db.scalars(select(UserStory).where(UserStory.id.in_(story_ids))).all()} if story_ids else {}
    by_story=[]
    for sid,story in stories.items():
        related=sorted([(r,i) for r in reports for i in r.items if i.user_story_id==sid],key=lambda x:(x[0].report_date,x[0].user.full_name,x[1].id)); progress=[i.progress_percent for _,i in related if i.progress_percent is not None]
        daily_details=[{"date":r.report_date.isoformat(),"member":r.user.full_name,"task_title":i.task_title,"completed":i.yesterday_work,"today_plan":i.today_plan,"progress_percent":i.progress_percent,"has_issue":i.has_issue,"issue_description":i.issue_description} for r,i in related]
        by_story.append({"story_id":sid,"code":story.code,"title":story.title,"members":unique([r.user.full_name for r,_ in related]),"work_done":unique([i.yesterday_work for _,i in related]),"daily_details":daily_details,"status":story.status.value,"start_progress":progress[0] if progress else None,"end_progress":progress[-1] if progress else story.progress_percent,"blockers":unique([i.issue_description for _,i in related if i.has_issue]),"due_date":story.due_date.isoformat() if story.due_date else None,"overdue":bool(story.due_date and story.due_date<end and story.status.value not in ("DONE","CLOSED"))})
    return {"period":{"start":start.isoformat(),"end":end.isoformat(),"workdays":len(workdays)},"options":{"include_next_plans":include_next_plans},"by_member":by_member,"by_story":by_story,"generated_note":"Dữ liệu được tổng hợp theo rule-based logic từ các Daily đã submit."}
def markdown(snapshot:dict)->str:
    p=snapshot["period"]; include_next_plans=snapshot.get("options",{}).get("include_next_plans",True); lines=[f"# Báo cáo tuần {p['start']} – {p['end']}","","## Theo thành viên"]
    for m in snapshot["by_member"]:
        lines += [f"### {m['full_name']}",f"- Daily: {m['submitted_days']} đã nộp, {m['missing_days']} thiếu",""]
        stories=m.get("story_details",[])
        if not stories: lines += ["- Không có công việc gắn với User Story.",""]
        for s in stories:
            lines += [f"#### {s['code']} — {s['title']}"]
            for task in s["tasks"]:
                progress=f" · Tiến độ {task['progress_percent']}%" if task.get("progress_percent") is not None else ""
                lines += [f"- **{task['date']}** — {task['task_title']}{progress}",f"  - Daily hoàn thành: {task.get('completed') or 'Không có'}"]
                if include_next_plans: lines += [f"  - Kế hoạch tiếp theo: {task.get('today_plan') or 'Không có'}"]
                if task.get("has_issue"): lines += [f"  - Blocker: {task.get('issue_description') or 'Có blocker'}"]
            lines += [""]
    return "\n".join(lines)
def csv_bytes(snapshot:dict)->bytes:
    include_next_plans=snapshot.get("options",{}).get("include_next_plans",True); out=io.StringIO(); w=csv.writer(out); headers=["Thành viên","User Story","Ngày","Task","Daily hoàn thành"]
    if include_next_plans: headers.append("Kế hoạch tiếp theo")
    headers += ["Tiến độ","Blocker"]; w.writerow(headers)
    for m in snapshot["by_member"]:
        stories=m.get("story_details",[])
        if not stories:
            row=[m["full_name"],"","","","Không có công việc gắn với User Story"]
            if include_next_plans: row.append("")
            row += ["",""]; w.writerow(row)
        for s in stories:
            for task in s["tasks"]:
                row=[m["full_name"],f"{s['code']} — {s['title']}",task["date"],task["task_title"],task.get("completed") or ""]
                if include_next_plans: row.append(task.get("today_plan") or "")
                row += [task.get("progress_percent") if task.get("progress_percent") is not None else "",task.get("issue_description") if task.get("has_issue") else ""]; w.writerow(row)
    return ('\ufeff'+out.getvalue()).encode('utf-8')
