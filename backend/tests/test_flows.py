from datetime import date,timedelta
from app.db.base import SessionLocal
from app.models.entities import DailyReport,DailyReportItem,DailyStatus,User,UserStory,UserStoryAssignment,StoryStatus,Priority

def test_login_success_and_failure(client):
    assert client.post("/api/auth/login",json={"username":"member","password":"Password1!"}).status_code==200
    assert client.post("/api/auth/login",json={"username":"member","password":"wrong"}).status_code==401

def test_inactive_cannot_login(client):
    assert client.post("/api/auth/login",json={"username":"inactive","password":"Password1!"}).status_code==403

def test_admin_resets_password_and_member_cannot_reset(client,admin_headers,member_headers):
    db=SessionLocal(); member=db.query(User).filter_by(username="member").one(); member_id=member.id; db.close()
    reset=client.post(f"/api/users/{member_id}/reset-password",headers=admin_headers,json={"new_password":"ResetPass1!"})
    assert reset.status_code==200
    assert client.post("/api/auth/login",json={"username":"member","password":"Password1!"}).status_code==401
    assert client.post("/api/auth/login",json={"username":"member","password":"ResetPass1!"}).status_code==200
    assert client.post(f"/api/users/{member_id}/reset-password",headers=member_headers,json={"new_password":"Blocked123!"}).status_code==403

def test_user_can_change_own_password(client,member_headers):
    changed=client.post("/api/auth/change-password",headers=member_headers,json={"current_password":"Password1!","new_password":"MyNewPass1!"})
    assert changed.status_code==200
    assert client.post("/api/auth/login",json={"username":"member","password":"Password1!"}).status_code==401
    assert client.post("/api/auth/login",json={"username":"member","password":"MyNewPass1!"}).status_code==200

def test_member_cannot_access_admin(client,member_headers):
    assert client.get("/api/users",headers=member_headers).status_code==403

def test_daily_unique_and_issue_validation(client,member_headers):
    today=date.today().isoformat(); payload={"items":[{"task_title":"Test","has_issue":False}]}
    assert client.put(f"/api/daily-reports/me/{today}",json=payload,headers=member_headers).status_code==200
    assert client.put(f"/api/daily-reports/me/{today}",json=payload,headers=member_headers).status_code==200
    db=SessionLocal(); assert db.query(DailyReport).count()==1; db.close()
    bad={"items":[{"task_title":"Test","has_issue":True,"issue_description":""}]}
    assert client.put(f"/api/daily-reports/me/{today}",json=bad,headers=member_headers).status_code==422

def test_future_submit_rejected(client,member_headers):
    future=(date.today()+timedelta(days=1)).isoformat()
    client.put(f"/api/daily-reports/me/{future}",json={"items":[{"task_title":"Future"}]},headers=member_headers)
    assert client.post(f"/api/daily-reports/me/{future}/submit",headers=member_headers).status_code==422

def test_member_can_edit_and_resubmit_today(client,member_headers):
    today=date.today().isoformat()
    assert client.put(f"/api/daily-reports/me/{today}",json={"items":[{"task_title":"First"}]},headers=member_headers).status_code==200
    assert client.post(f"/api/daily-reports/me/{today}/submit",headers=member_headers).status_code==200
    updated=client.put(f"/api/daily-reports/me/{today}",json={"items":[{"task_title":"Corrected"}]},headers=member_headers)
    assert updated.status_code==200
    assert client.post(f"/api/daily-reports/me/{today}/submit",headers=member_headers).status_code==200

def test_past_daily_requires_admin_reopen_and_keeps_audit(client,admin_headers,member_headers):
    db=SessionLocal(); member=db.query(User).filter_by(username="member").one(); yesterday=date.today()-timedelta(days=1)
    report=DailyReport(user_id=member.id,report_date=yesterday,status=DailyStatus.SUBMITTED); report.items=[DailyReportItem(task_title="Original")]
    db.add(report); db.commit(); report_id=report.id; db.close()
    payload={"items":[{"task_title":"Corrected past task"}]}
    assert client.put(f"/api/daily-reports/me/{yesterday.isoformat()}",json=payload,headers=member_headers).status_code==409
    assert client.post(f"/api/admin/daily-reports/{report_id}/reopen",json={"reason":"Need correction"},headers=member_headers).status_code==403
    reopened=client.post(f"/api/admin/daily-reports/{report_id}/reopen",json={"reason":"Nhập nhầm nội dung task"},headers=admin_headers)
    assert reopened.status_code==200
    assert reopened.json()["status"]=="DRAFT" and reopened.json()["is_reopened"] is True
    history=client.get(f"/api/admin/daily-reports/{report_id}/reopen-history",headers=admin_headers).json()
    assert history[0]["reason"]=="Nhập nhầm nội dung task" and history[0]["reopened_by_name"]=="Admin"
    assert client.put(f"/api/daily-reports/me/{yesterday.isoformat()}",json=payload,headers=member_headers).status_code==200
    resubmitted=client.post(f"/api/daily-reports/me/{yesterday.isoformat()}/submit",headers=member_headers)
    assert resubmitted.status_code==200 and resubmitted.json()["is_reopened"] is False
    assert client.post(f"/api/daily-reports/me/{yesterday.isoformat()}/submit",headers=member_headers).status_code==409

def test_member_cannot_edit_other_report(client,member_headers):
    assert client.patch("/api/admin/daily-reports/999",json={"items":[{"task_title":"x"}]},headers=member_headers).status_code==403

def test_admin_filters_team_daily_by_date_range(client,admin_headers):
    db=SessionLocal(); member=db.query(User).filter_by(username="member").one(); today=date.today(); yesterday=today-timedelta(days=1)
    db.add_all([DailyReport(user_id=member.id,report_date=yesterday,status=DailyStatus.SUBMITTED),DailyReport(user_id=member.id,report_date=today,status=DailyStatus.SUBMITTED)]); db.commit(); db.close()
    response=client.get(f"/api/admin/daily-reports?date_from={yesterday.isoformat()}&date_to={today.isoformat()}",headers=admin_headers)
    assert response.status_code==200
    member_rows=[row for row in response.json() if row["user"]["username"]=="member"]
    assert [row["report_date"] for row in member_rows]==[yesterday.isoformat(),today.isoformat()]

def test_dashboard_blockers_query(client,admin_headers):
    db=SessionLocal(); admin=db.query(User).filter_by(username="admin").one(); member=db.query(User).filter_by(username="member").one(); today=date.today()
    story=UserStory(code="US-B",title="Blocked story",status=StoryStatus.BLOCKED,priority=Priority.HIGH,progress_percent=10,created_by=admin.id); db.add(story); db.flush()
    report=DailyReport(user_id=member.id,report_date=today,status=DailyStatus.SUBMITTED); report.items=[DailyReportItem(user_story_id=story.id,task_title="Blocked task",has_issue=True,issue_description="Waiting for access")]; db.add(report); db.commit(); db.close()
    response=client.get("/api/dashboard/blockers",headers=admin_headers)
    assert response.status_code==200
    assert response.json()[0]["story_code"]=="US-B"

def test_admin_can_edit_and_delete_unlinked_story(client,admin_headers):
    created=client.post("/api/user-stories",headers=admin_headers,json={"code":"US-EDIT","title":"Before","priority":"MEDIUM","status":"TODO","progress_percent":0,"assignee_ids":[]})
    assert created.status_code==201
    story_id=created.json()["id"]
    updated=client.patch(f"/api/user-stories/{story_id}",headers=admin_headers,json={"code":"US-DONE","title":"After","status":"DONE","progress_percent":100})
    assert updated.status_code==200
    assert updated.json()["code"]=="US-DONE"
    assert client.delete(f"/api/user-stories/{story_id}",headers=admin_headers).status_code==204

def test_admin_cannot_delete_story_with_daily_history(client,admin_headers):
    db=SessionLocal(); admin=db.query(User).filter_by(username="admin").one(); member=db.query(User).filter_by(username="member").one(); story=UserStory(code="US-HISTORY",title="History",status=StoryStatus.IN_PROGRESS,priority=Priority.HIGH,progress_percent=20,created_by=admin.id); db.add(story); db.flush(); report=DailyReport(user_id=member.id,report_date=date.today(),status=DailyStatus.SUBMITTED); report.items=[DailyReportItem(user_story_id=story.id,task_title="Historical task",has_issue=False)]; db.add(report); db.commit(); story_id=story.id; db.close()
    response=client.delete(f"/api/user-stories/{story_id}",headers=admin_headers)
    assert response.status_code==409

def test_member_sees_and_logs_unassigned_active_story(client,member_headers):
    db=SessionLocal(); admin=db.query(User).filter_by(username="admin").one()
    active=UserStory(code="US-ACTIVE",title="Available to everyone",status=StoryStatus.TODO,priority=Priority.MEDIUM,progress_percent=0,created_by=admin.id)
    closed=UserStory(code="US-CLOSED",title="Not available",status=StoryStatus.CLOSED,priority=Priority.LOW,progress_percent=100,created_by=admin.id)
    db.add_all([active,closed]); db.commit(); active_id=active.id; closed_id=closed.id; db.close()
    stories=client.get("/api/user-stories?page_size=100",headers=member_headers)
    assert stories.status_code==200
    assert [item["code"] for item in stories.json()["items"]]==["US-ACTIVE"]
    today=date.today().isoformat()
    saved=client.put(f"/api/daily-reports/me/{today}",headers=member_headers,json={"items":[{"user_story_id":active_id,"task_title":"Log without assignment","has_issue":False}]})
    assert saved.status_code==200
    rejected=client.put(f"/api/daily-reports/me/{today}",headers=member_headers,json={"items":[{"user_story_id":closed_id,"task_title":"Closed task","has_issue":False}]})
    assert rejected.status_code==422

def test_weekly_grouping_and_finalized_snapshot(client,admin_headers):
    db=SessionLocal(); admin=db.query(User).filter_by(username="admin").one(); member=db.query(User).filter_by(username="member").one(); today=date.today()
    story=UserStory(code="US-T",title="Test story",status=StoryStatus.IN_PROGRESS,priority=Priority.HIGH,progress_percent=50,created_by=admin.id); db.add(story); db.flush(); story.assignments=[UserStoryAssignment(user_id=member.id)]
    report=DailyReport(user_id=member.id,report_date=today,status=DailyStatus.SUBMITTED); report.items=[DailyReportItem(user_story_id=story.id,task_title="Task A",yesterday_work="Done A",today_plan="Plan B",has_issue=False,progress_percent=50)]; db.add(report); db.commit(); db.close()
    preview=client.post("/api/weekly-reports/preview",json={"week_start":today.isoformat(),"week_end":today.isoformat()},headers=admin_headers).json()
    assert all(item["full_name"]!="Admin" for item in preview["by_member"])
    member_summary=next(x for x in preview["by_member"] if x["user_id"]==member.id); assert member_summary["submitted_days"]==1; assert preview["by_story"][0]["code"]=="US-T"
    member_story=member_summary["story_details"][0]; assert member_story["code"]=="US-T"; assert member_story["tasks"][0]["task_title"]=="Task A"; assert member_story["tasks"][0]["completed"]=="Done A"
    detail=preview["by_story"][0]["daily_details"][0]; assert detail["date"]==today.isoformat(); assert detail["member"]=="Member"; assert detail["task_title"]=="Task A"; assert detail["completed"]=="Done A"; assert detail["today_plan"]=="Plan B"
    generated=client.post("/api/weekly-reports/generate",json={"week_start":today.isoformat(),"week_end":today.isoformat()},headers=admin_headers).json(); rid=generated["id"]; before=generated["snapshot"]
    markdown_export=client.get(f"/api/weekly-reports/{rid}/export?format=markdown",headers=admin_headers); assert "### Member" in markdown_export.text; assert "#### US-T — Test story" in markdown_export.text; assert "Task A" in markdown_export.text
    csv_export=client.get(f"/api/weekly-reports/{rid}/export?format=csv",headers=admin_headers); assert "Task A" in csv_export.text; assert "Done A" in csv_export.text
    hidden=client.post("/api/weekly-reports/generate",json={"week_start":today.isoformat(),"week_end":today.isoformat(),"include_next_plans":False},headers=admin_headers).json(); assert hidden["snapshot"]["options"]["include_next_plans"] is False
    hidden_markdown=client.get(f"/api/weekly-reports/{hidden['id']}/export?format=markdown",headers=admin_headers); assert "Kế hoạch tiếp theo" not in hidden_markdown.text; assert "Plan B" not in hidden_markdown.text
    hidden_csv=client.get(f"/api/weekly-reports/{hidden['id']}/export?format=csv",headers=admin_headers); assert "Kế hoạch tiếp theo" not in hidden_csv.text; assert "Plan B" not in hidden_csv.text
    assert client.post(f"/api/weekly-reports/{rid}/finalize",headers=admin_headers).json()["status"]=="FINALIZED"
    db=SessionLocal(); db.query(DailyReportItem).first().yesterday_work="CHANGED"; db.commit(); db.close()
    assert client.get(f"/api/weekly-reports/{rid}",headers=admin_headers).json()["snapshot"]==before
