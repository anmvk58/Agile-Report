from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from app.models.entities import DailyStatus, Priority, Role, StoryStatus, WeeklyStatus

class ORMModel(BaseModel): model_config=ConfigDict(from_attributes=True)
class LoginRequest(BaseModel): username: str; password: str
class TokenResponse(BaseModel): access_token: str; token_type: str="bearer"
class ChangePassword(BaseModel): current_password: str; new_password: str=Field(min_length=8)
class UserBase(BaseModel):
    username: str=Field(min_length=3,max_length=50); full_name: str=Field(min_length=1,max_length=120); email: EmailStr; role: Role=Role.MEMBER
class UserCreate(UserBase): password: str=Field(min_length=8)
class UserUpdate(BaseModel): full_name: Optional[str]=None; email: Optional[EmailStr]=None; role: Optional[Role]=None
class UserOut(UserBase, ORMModel): id:int; is_active:bool; created_at:datetime; updated_at:datetime
class StatusUpdate(BaseModel): is_active: bool
class PasswordReset(BaseModel): new_password: str=Field(min_length=8)

class StoryBase(BaseModel):
    code:str=Field(min_length=2,max_length=30); title:str=Field(min_length=1,max_length=255); description:Optional[str]=None
    status:StoryStatus=StoryStatus.TODO; priority:Priority=Priority.MEDIUM; start_date:Optional[date]=None; due_date:Optional[date]=None
    progress_percent:int=Field(default=0,ge=0,le=100); assignee_ids:list[int]=[]
    @model_validator(mode="after")
    def dates(self):
        if self.start_date and self.due_date and self.due_date < self.start_date: raise ValueError("Hạn hoàn thành không được trước ngày bắt đầu")
        return self
class StoryCreate(StoryBase): pass
class StoryUpdate(BaseModel):
    code:Optional[str]=Field(default=None,min_length=2,max_length=30); title:Optional[str]=None; description:Optional[str]=None; status:Optional[StoryStatus]=None; priority:Optional[Priority]=None
    start_date:Optional[date]=None; due_date:Optional[date]=None; progress_percent:Optional[int]=Field(default=None,ge=0,le=100); assignee_ids:Optional[list[int]]=None
class StoryOut(ORMModel):
    id:int; code:str; title:str; description:Optional[str]; status:StoryStatus; priority:Priority; start_date:Optional[date]; due_date:Optional[date]
    progress_percent:int; created_by:int; created_at:datetime; updated_at:datetime; closed_at:Optional[datetime]; assignees:list[UserOut]=[]

class DailyItemIn(BaseModel):
    id:Optional[int]=None; user_story_id:Optional[int]=None; task_title:str=Field(min_length=1,max_length=255)
    yesterday_work:Optional[str]=None; today_plan:Optional[str]=None; has_issue:bool=False; issue_description:Optional[str]=None
    progress_percent:Optional[int]=Field(default=None,ge=0,le=100)
    @model_validator(mode="after")
    def issue_required(self):
        if self.has_issue and not (self.issue_description or "").strip(): raise ValueError("Nội dung blocker là bắt buộc")
        return self
class DailyUpsert(BaseModel): general_note:Optional[str]=None; items:list[DailyItemIn]=Field(min_length=1)
class DailyItemOut(DailyItemIn, ORMModel):
    id:int; created_at:datetime; updated_at:datetime
    story_code:Optional[str]=None; story_title:Optional[str]=None
class DailyOut(ORMModel):
    id:int; user_id:int; report_date:date; general_note:Optional[str]; status:DailyStatus; submitted_at:Optional[datetime]
    is_reopened:bool=False; created_at:datetime; updated_at:datetime; items:list[DailyItemOut]; user:Optional[UserOut]=None
class DailyReopenRequest(BaseModel):
    reason:str=Field(min_length=3,max_length=500)
class DailyReopenAuditOut(BaseModel):
    id:int; reason:str; reopened_at:datetime; reopened_by:int; reopened_by_name:str

class WeeklyRange(BaseModel):
    week_start:date; week_end:date; include_next_plans:bool=True
    @model_validator(mode="after")
    def valid_range(self):
        if self.week_end < self.week_start: raise ValueError("Ngày kết thúc phải sau ngày bắt đầu")
        if (self.week_end-self.week_start).days > 31: raise ValueError("Khoảng báo cáo tối đa 31 ngày")
        return self
class WeeklyOut(ORMModel):
    id:int; week_start:date; week_end:date; generated_by:int; generated_at:datetime; status:WeeklyStatus; snapshot:dict
