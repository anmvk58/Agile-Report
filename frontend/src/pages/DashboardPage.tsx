import {useEffect,useState} from 'react';
import {AlertTriangle,BookOpenCheck,CheckCircle2,Clock3,Users} from 'lucide-react';
import {api} from '../api/client';
import {Loading} from '../components/ui';
import type {User} from '../types';

type Summary={active_members:number;submitted_today:number;missing_today:number;active_stories:number;blocked_stories:number;issues_today:number;missing_members:User[];week_progress:{date:string;submitted:number;total:number}[]};
type Blocker={date:string;member:string;task_title:string;issue:string;story_code?:string};

export function DashboardPage({isAdmin,name}:{isAdmin:boolean;name:string}){
  const [data,setData]=useState<Summary|null>(null);
  const [blockers,setBlockers]=useState<Blocker[]>([]);
  const [error,setError]=useState('');
  const [reload,setReload]=useState(0);

  useEffect(()=>{
    if(!isAdmin)return;
    setError('');
    Promise.all([api<Summary>('/dashboard/summary'),api<Blocker[]>('/dashboard/blockers')])
      .then(([summary,latestBlockers])=>{setData(summary);setBlockers(latestBlockers)})
      .catch(err=>setError(err instanceof Error?err.message:'Không thể tải dữ liệu Dashboard'));
  },[isAdmin,reload]);

  if(!isAdmin)return <MemberOverview name={name}/>;
  if(error)return <div className="card mx-auto max-w-xl p-8 text-center"><AlertTriangle className="mx-auto text-red-500" size={34}/><h2 className="mt-4 text-xl font-bold">Không thể tải Dashboard</h2><p className="mt-2 text-sm text-slate-500">{error}</p><button className="btn-primary mt-5" onClick={()=>setReload(value=>value+1)}>Thử lại</button></div>;
  if(!data)return <Loading/>;

  const cards=[['Thành viên active',data.active_members,Users,'bg-blue-50 text-blue-700'],['Đã submit hôm nay',data.submitted_today,CheckCircle2,'bg-emerald-50 text-emerald-700'],['Chưa submit',data.missing_today,Clock3,'bg-amber-50 text-amber-700'],['Story đang làm',data.active_stories,BookOpenCheck,'bg-violet-50 text-violet-700'],['Story bị chặn',data.blocked_stories,AlertTriangle,'bg-red-50 text-red-700']] as const;
  return <div><div className="mb-7"><p className="mb-1 text-sm font-bold uppercase tracking-widest text-brand">Toàn cảnh hôm nay</p><h1 className="text-3xl font-extrabold">Dashboard</h1><p className="mt-2 text-slate-500">Những điểm cần chú ý để team giữ đúng nhịp.</p></div><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">{cards.map(([label,value,Icon,color])=><div className="card p-5" key={label}><div className={`mb-4 inline-flex rounded-xl p-2.5 ${color}`}><Icon size={21}/></div><div className="text-3xl font-extrabold">{value}</div><div className="mt-1 text-sm text-slate-500">{label}</div></div>)}</div><div className="mt-6 grid gap-6 xl:grid-cols-5"><section className="card p-6 xl:col-span-3"><h2 className="text-lg font-bold">Blocker mới nhất</h2><div className="mt-4 space-y-3">{blockers.slice(0,6).map((blocker,index)=><div key={index} className="flex gap-3 rounded-xl border border-red-100 bg-red-50/60 p-4"><AlertTriangle className="shrink-0 text-red-500" size={19}/><div><div className="font-bold">{blocker.story_code&&<span className="mr-2 text-red-700">{blocker.story_code}</span>}{blocker.task_title}</div><p className="mt-1 text-sm text-slate-600">{blocker.issue}</p><p className="mt-2 text-xs text-slate-400">{blocker.member} · {blocker.date}</p></div></div>)}{blockers.length===0&&<p className="py-8 text-center text-slate-500">Không có blocker mới 🎉</p>}</div></section><section className="card p-6 xl:col-span-2"><h2 className="text-lg font-bold">Chưa khai báo hôm nay</h2><div className="mt-4 space-y-2">{data.missing_members.map(member=><div key={member.id} className="flex items-center gap-3 rounded-xl bg-stone-50 p-3"><div className="grid h-9 w-9 place-items-center rounded-full bg-navy text-sm font-bold text-white">{member.full_name[0]}</div><div><div className="font-semibold">{member.full_name}</div><div className="text-xs text-slate-500">@{member.username}</div></div></div>)}{data.missing_members.length===0&&<p className="py-8 text-center text-emerald-600">Cả team đã hoàn thành!</p>}</div></section></div></div>;
}

function MemberOverview({name}:{name:string}){
  return <div><div className="mb-8 rounded-3xl bg-navy p-8 text-white"><p className="text-orange-300">Xin chào, {name}</p><h1 className="mt-2 text-4xl font-extrabold">Hôm nay bạn sẽ tạo ra điều gì?</h1><p className="mt-3 max-w-xl text-slate-300">Hãy cập nhật Daily trong vài phút để cả team cùng nhìn thấy tiến độ và hỗ trợ blocker sớm.</p><a href="/daily" className="btn-primary mt-6">Bắt đầu Daily hôm nay</a></div><div className="grid gap-5 md:grid-cols-3">{[['01','Ghi kết quả','Nêu đầu ra đã hoàn thành, không chỉ hoạt động.'],['02','Chốt kế hoạch','Chọn mục tiêu cụ thể và có thể kiểm chứng.'],['03','Báo blocker sớm','Nói rõ bạn đang cần ai hỗ trợ điều gì.']].map(item=><div className="card p-6" key={item[0]}><div className="text-3xl font-extrabold text-orange-200">{item[0]}</div><h3 className="mt-4 font-bold">{item[1]}</h3><p className="mt-2 text-sm text-slate-500">{item[2]}</p></div>)}</div></div>;
}
