import {FormEvent,useEffect,useState} from 'react';
import {AlertTriangle,Pencil,Plus,Search,Trash2} from 'lucide-react';
import {api} from '../api/client';
import {Empty,Loading,Modal,StatusBadge,Toast,ToastData} from '../components/ui';
import type {Page,Story,User} from '../types';

type StoryForm={code:string;title:string;description:string;status:Story['status'];priority:Story['priority'];start_date:string;due_date:string;progress_percent:number;assignee_ids:number[]};
const emptyForm=():StoryForm=>({code:'',title:'',description:'',status:'TODO',priority:'MEDIUM',start_date:'',due_date:'',progress_percent:0,assignee_ids:[]});

export function StoriesPage({isAdmin}:{isAdmin:boolean}){
  const [data,setData]=useState<Page<Story>|null>(null);
  const [users,setUsers]=useState<User[]>([]);
  const [search,setSearch]=useState('');
  const [editingId,setEditingId]=useState<number|null>(null);
  const [modal,setModal]=useState(false);
  const [form,setForm]=useState<StoryForm>(emptyForm());
  const [saving,setSaving]=useState(false);
  const [toast,setToast]=useState<ToastData>(null);

  const load=()=>api<Page<Story>>(`/user-stories?page_size=100&search=${encodeURIComponent(search)}`).then(setData).catch(error=>setToast({kind:'error',message:error instanceof Error?error.message:'Không thể tải User Story'}));
  useEffect(()=>{load();if(isAdmin)api<Page<User>>('/users?page_size=100').then(result=>setUsers(result.items.filter(user=>user.is_active)))},[]);

  const openCreate=()=>{setEditingId(null);setForm(emptyForm());setModal(true)};
  const openEdit=(story:Story)=>{setEditingId(story.id);setForm({code:story.code,title:story.title,description:story.description??'',status:story.status,priority:story.priority,start_date:story.start_date??'',due_date:story.due_date??'',progress_percent:story.progress_percent,assignee_ids:story.assignees.map(user=>user.id)});setModal(true)};

  const submit=async(event:FormEvent)=>{
    event.preventDefault();setSaving(true);
    const payload={...form,start_date:form.start_date||null,due_date:form.due_date||null};
    try{
      if(editingId)await api(`/user-stories/${editingId}`,{method:'PATCH',body:JSON.stringify(payload)});
      else await api('/user-stories',{method:'POST',body:JSON.stringify(payload)});
      setModal(false);setToast({kind:'success',message:editingId?'Đã cập nhật User Story':'Đã tạo User Story'});await load();
    }catch(error){setToast({kind:'error',message:error instanceof Error?error.message:'Không thể lưu User Story'})}
    finally{setSaving(false)}
  };

  const remove=async(story:Story)=>{
    if(!confirm(`Xóa User Story ${story.code} — ${story.title}?\n\nUser Story đã có lịch sử Daily sẽ không thể xóa.`))return;
    try{await api(`/user-stories/${story.id}`,{method:'DELETE'});setToast({kind:'success',message:`Đã xóa ${story.code}`});await load()}
    catch(error){setToast({kind:'error',message:error instanceof Error?error.message:'Không thể xóa User Story'})}
  };

  return <div><Toast toast={toast} clear={()=>setToast(null)}/><div className="mb-7 flex flex-wrap items-end justify-between gap-4"><div><p className="mb-1 text-sm font-bold uppercase tracking-widest text-brand">Product backlog</p><h1 className="text-3xl font-extrabold">User Stories</h1>{!isAdmin&&<p className="mt-2 text-sm text-slate-500">Tất cả User Story đang active đều có thể được chọn khi khai báo Daily.</p>}</div>{isAdmin&&<button className="btn-primary" onClick={openCreate}><Plus size={18}/>Tạo User Story</button>}</div><div className="card mb-5 flex gap-3 p-4"><div className="relative flex-1"><Search className="absolute left-3 top-3 text-slate-400" size={19}/><input className="field pl-10" placeholder="Tìm theo mã hoặc tiêu đề..." value={search} onChange={event=>setSearch(event.target.value)} onKeyDown={event=>event.key==='Enter'&&load()}/></div><button className="btn-secondary" onClick={load}>Tìm kiếm</button></div>{!data?<Loading/>:data.items.length===0?<Empty title="Không có User Story active" detail={isAdmin?'Tạo User Story đầu tiên để bắt đầu quản lý backlog.':'Hiện chưa có User Story nào khả dụng để log task.'}/>:<div className="grid gap-4 lg:grid-cols-2">{data.items.map(story=><article key={story.id} className="card p-5"><div className="flex items-start justify-between gap-3"><div><div className="mb-2 flex flex-wrap items-center gap-2"><span className="font-extrabold text-brand">{story.code}</span><StatusBadge status={story.status}/>{story.priority==='CRITICAL'&&<span className="badge bg-red-100 text-red-700">Khẩn cấp</span>}</div><h2 className="text-lg font-bold">{story.title}</h2></div><div className="flex items-center gap-1">{story.due_date&&new Date(story.due_date)<new Date()&&story.status!=='DONE'&&story.status!=='CLOSED'&&<AlertTriangle className="mr-1 text-red-500"/>}{isAdmin&&<><button aria-label={`Sửa ${story.code}`} title="Sửa User Story" onClick={()=>openEdit(story)} className="rounded-lg p-2 text-slate-500 hover:bg-blue-50 hover:text-blue-700"><Pencil size={18}/></button><button aria-label={`Xóa ${story.code}`} title="Xóa User Story" onClick={()=>remove(story)} className="rounded-lg p-2 text-slate-500 hover:bg-red-50 hover:text-red-700"><Trash2 size={18}/></button></>}</div></div><p className="mt-2 line-clamp-2 text-sm text-slate-500">{story.description||'Chưa có mô tả'}</p><div className="mt-5"><div className="mb-2 flex justify-between text-xs font-bold"><span>Tiến độ</span><span>{story.progress_percent}%</span></div><div className="h-2 rounded-full bg-stone-100"><div className="h-full rounded-full bg-brand" style={{width:`${story.progress_percent}%`}}/></div></div><div className="mt-4 flex items-center justify-between text-xs text-slate-500"><span>{story.assignees.length} người phụ trách</span><span>Hạn: {story.due_date?new Date(story.due_date).toLocaleDateString('vi-VN'):'—'}</span></div></article>)}</div>}{modal&&<StoryModal form={form} setForm={setForm} users={users} editing={editingId!==null} saving={saving} submit={submit} close={()=>setModal(false)}/>}</div>;
}

function StoryModal({form,setForm,users,editing,saving,submit,close}:{form:StoryForm;setForm:(value:StoryForm)=>void;users:User[];editing:boolean;saving:boolean;submit:(event:FormEvent)=>void;close:()=>void}){
  return <Modal title={editing?'Sửa User Story':'Tạo User Story'} onClose={close}><form onSubmit={submit} className="space-y-4"><div className="grid gap-4 sm:grid-cols-3"><div><label className="label">Mã</label><input className="field" required value={form.code} onChange={event=>setForm({...form,code:event.target.value.toUpperCase()})} placeholder="US-001"/></div><div className="sm:col-span-2"><label className="label">Tiêu đề</label><input className="field" required value={form.title} onChange={event=>setForm({...form,title:event.target.value})}/></div></div><div><label className="label">Mô tả</label><textarea className="field min-h-24" value={form.description} onChange={event=>setForm({...form,description:event.target.value})}/></div><div className="grid gap-4 sm:grid-cols-2"><div><label className="label">Trạng thái</label><select className="field" value={form.status} onChange={event=>setForm({...form,status:event.target.value as Story['status']})}><option value="TODO">Cần làm</option><option value="IN_PROGRESS">Đang làm</option><option value="BLOCKED">Bị chặn</option><option value="DONE">Hoàn thành</option><option value="CLOSED">Đã đóng</option></select></div><div><label className="label">Ưu tiên</label><select className="field" value={form.priority} onChange={event=>setForm({...form,priority:event.target.value as Story['priority']})}><option value="LOW">Thấp</option><option value="MEDIUM">Trung bình</option><option value="HIGH">Cao</option><option value="CRITICAL">Khẩn cấp</option></select></div><div><label className="label">Ngày bắt đầu</label><input type="date" className="field" value={form.start_date} onChange={event=>setForm({...form,start_date:event.target.value})}/></div><div><label className="label">Hạn hoàn thành</label><input type="date" className="field" value={form.due_date} onChange={event=>setForm({...form,due_date:event.target.value})}/></div></div><div><label className="label">Tiến độ: {form.progress_percent}%</label><input type="range" min="0" max="100" step="5" className="w-full accent-orange-600" value={form.progress_percent} onChange={event=>setForm({...form,progress_percent:Number(event.target.value)})}/></div><div><label className="label">Giao cho thành viên</label><div className="grid max-h-36 gap-2 overflow-auto rounded-xl border border-stone-200 p-3 sm:grid-cols-2">{users.length?users.map(user=><label key={user.id} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.assignee_ids.includes(user.id)} onChange={event=>setForm({...form,assignee_ids:event.target.checked?[...form.assignee_ids,user.id]:form.assignee_ids.filter(id=>id!==user.id)})}/>{user.full_name}</label>):<p className="text-sm text-slate-500">Chưa có thành viên active.</p>}</div></div><div className="flex justify-end gap-3"><button type="button" className="btn-secondary" onClick={close}>Hủy</button><button className="btn-primary" disabled={saving}>{saving?'Đang lưu...':editing?'Lưu thay đổi':'Tạo User Story'}</button></div></form></Modal>;
}
