export type Role='ADMIN'|'MEMBER';
export interface User{id:number;username:string;full_name:string;email:string;role:Role;is_active:boolean}
export interface Story{id:number;code:string;title:string;description?:string;status:'TODO'|'IN_PROGRESS'|'BLOCKED'|'DONE'|'CLOSED';priority:'LOW'|'MEDIUM'|'HIGH'|'CRITICAL';progress_percent:number;start_date?:string;due_date?:string;assignees:User[]}
export interface DailyItem{id?:number;user_story_id:number|null;story_code?:string;story_title?:string;task_title:string;yesterday_work:string;today_plan:string;has_issue:boolean;issue_description:string;progress_percent:number|null}
export interface Daily{id:number;user_id:number;report_date:string;general_note:string;status:'DRAFT'|'SUBMITTED';submitted_at?:string;is_reopened:boolean;updated_at:string;items:DailyItem[];user?:User}
export interface Page<T>{items:T[];total:number;page:number;page_size:number}
