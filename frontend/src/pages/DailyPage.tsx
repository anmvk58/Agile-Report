import {useEffect, useState} from 'react';
import {AlertTriangle, Calendar, LockKeyhole, Plus, Save, Send, Trash2} from 'lucide-react';
import {api} from '../api/client';
import {Loading, StatusBadge, Toast, type ToastData} from '../components/ui';
import type {Daily, DailyItem, Page, Story} from '../types';

const today = () => new Intl.DateTimeFormat('en-CA', {timeZone: 'Asia/Ho_Chi_Minh'}).format(new Date());
const blank = (): DailyItem => ({user_story_id: null, task_title: '', yesterday_work: '', today_plan: '', has_issue: false, issue_description: '', progress_percent: null});

export function DailyPage() {
  const [date, setDate] = useState(today());
  const [items, setItems] = useState<DailyItem[]>([blank()]);
  const [note, setNote] = useState('');
  const [status, setStatus] = useState<'DRAFT' | 'SUBMITTED'>('DRAFT');
  const [isReopened, setIsReopened] = useState(false);
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [toast, setToast] = useState<ToastData>(null);
  const [errors, setErrors] = useState<Record<number, string>>({});
  const locked = date < today() && !isReopened;

  useEffect(() => { api<Page<Story>>('/user-stories?page_size=100').then((result) => setStories(result.items)); }, []);
  useEffect(() => {
    setLoading(true);
    api<Daily>(`/daily-reports/me/${date}`)
      .then((report) => { setItems(report.items); setNote(report.general_note ?? ''); setStatus(report.status); setIsReopened(report.is_reopened); })
      .catch((error) => {
        if ((error as {status?: number}).status === 404) { setItems([blank()]); setNote(''); setStatus('DRAFT'); setIsReopened(false); }
        else setToast({kind: 'error', message: error.message});
      })
      .finally(() => { setLoading(false); setDirty(false); });
  }, [date]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty) { event.preventDefault(); event.returnValue = ''; } };
    addEventListener('beforeunload', warn);
    return () => removeEventListener('beforeunload', warn);
  }, [dirty]);

  const update = (index: number, key: keyof DailyItem, value: unknown) => { setItems((current) => current.map((item, itemIndex) => itemIndex === index ? {...item, [key]: value} : item)); setDirty(true); };
  const validate = () => {
    const nextErrors: Record<number, string> = {};
    items.forEach((item, index) => {
      if (!item.task_title.trim()) nextErrors[index] = 'Vui lòng nhập tên công việc';
      else if (item.has_issue && !item.issue_description.trim()) nextErrors[index] = 'Vui lòng mô tả blocker';
    });
    setErrors(nextErrors);
    return !Object.keys(nextErrors).length;
  };
  const save = async () => {
    if (locked || !validate()) return false;
    setSaving(true);
    try {
      const report = await api<Daily>(`/daily-reports/me/${date}`, {method: 'PUT', body: JSON.stringify({general_note: note, items})});
      setItems(report.items); setStatus(report.status); setIsReopened(report.is_reopened); setDirty(false);
      setToast({kind: 'success', message: 'Đã lưu bản nháp'});
      return true;
    } catch (error) {
      setToast({kind: 'error', message: error instanceof Error ? error.message : 'Không thể lưu'});
      return false;
    } finally { setSaving(false); }
  };
  const submit = async () => {
    if (!(await save())) return;
    try {
      const report = await api<Daily>(`/daily-reports/me/${date}/submit`, {method: 'POST'});
      setStatus(report.status); setIsReopened(report.is_reopened); setDirty(false);
      setToast({kind: 'success', message: 'Daily đã được gửi thành công'});
    } catch (error) { setToast({kind: 'error', message: error instanceof Error ? error.message : 'Không thể submit'}); }
  };

  if (loading) return <Loading />;
  return (
    <div>
      <Toast toast={toast} clear={() => setToast(null)} />
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div><p className="mb-1 text-sm font-bold uppercase tracking-widest text-brand">Không gian tập trung</p><h1 className="text-3xl font-extrabold">Daily của tôi</h1><p className="mt-2 text-slate-500">Ghi nhanh điều quan trọng, làm rõ bước tiếp theo.</p></div>
        <div className="flex items-center gap-3"><StatusBadge status={status} /><label className="flex items-center gap-2 rounded-xl border border-stone-300 bg-white px-3 py-2"><Calendar size={17} /><input type="date" value={date} onChange={(event) => { if (dirty && !confirm('Bạn có thay đổi chưa lưu. Vẫn chuyển ngày?')) return; setDate(event.target.value); }} className="bg-transparent font-semibold" /></label></div>
      </div>

      {locked && <div className="mb-5 flex gap-3 rounded-xl border border-stone-300 bg-stone-100 p-4 text-sm text-slate-700"><LockKeyhole className="shrink-0" size={20} /><div><b>Daily này đã được khóa.</b><p className="mt-1">Bạn chỉ có thể xem nội dung. Hãy liên hệ Admin và cung cấp lý do nếu cần chỉnh sửa.</p></div></div>}
      {date < today() && isReopened && <div className="mb-5 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"><AlertTriangle className="shrink-0" size={20} /><div><b>Admin đã mở lại Daily này.</b><p className="mt-1">Sau khi bạn submit, báo cáo sẽ tự động khóa lại.</p></div></div>}

      <fieldset disabled={locked || saving} className={locked ? 'opacity-75' : ''}>
        <div className="space-y-4">
          {items.map((item, index) => (
            <section key={item.id ?? index} className="card overflow-hidden">
              <div className="flex items-center justify-between border-b border-stone-200 bg-stone-50 px-5 py-3"><div className="flex items-center gap-2"><span className="grid h-7 w-7 place-items-center rounded-lg bg-navy text-xs font-bold text-white">{index + 1}</span><span className="font-bold">Công việc</span></div><button type="button" aria-label="Xóa task" disabled={items.length === 1 || locked} onClick={() => { setItems((current) => current.filter((_, itemIndex) => itemIndex !== index)); setDirty(true); }} className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-30"><Trash2 size={18} /></button></div>
              <div className="grid gap-5 p-5 lg:grid-cols-2">
                <div><label className="label">User Story</label><select className="field" value={item.user_story_id ?? ''} onChange={(event) => update(index, 'user_story_id', event.target.value ? Number(event.target.value) : null)}><option value="">Không thuộc User Story</option>{stories.filter((story) => story.status !== 'CLOSED' || story.id === item.user_story_id).map((story) => <option key={story.id} value={story.id}>{story.code} — {story.title}</option>)}</select></div>
                <div><label className="label">Tên task / công việc <span className="text-brand">*</span></label><input className={`field ${errors[index] ? 'border-red-500' : ''}`} value={item.task_title} onChange={(event) => update(index, 'task_title', event.target.value)} placeholder="Ví dụ: Hoàn thiện API đăng nhập" />{errors[index] && <p className="mt-1 text-sm text-red-600">{errors[index]}</p>}</div>
                <div><label className="label">Hôm qua đã làm gì?</label><textarea className="field min-h-28 resize-y" value={item.yesterday_work ?? ''} onChange={(event) => update(index, 'yesterday_work', event.target.value)} placeholder="Kết quả cụ thể đã hoàn thành..." /></div>
                <div><label className="label">Hôm nay dự kiến làm gì?</label><textarea className="field min-h-28 resize-y" value={item.today_plan ?? ''} onChange={(event) => update(index, 'today_plan', event.target.value)} placeholder="Mục tiêu và đầu ra mong đợi..." /></div>
                <div className="flex flex-wrap items-center gap-5 rounded-xl bg-stone-50 p-4 lg:col-span-2"><label className="flex cursor-pointer items-center gap-2 font-semibold"><input type="checkbox" checked={item.has_issue} onChange={(event) => update(index, 'has_issue', event.target.checked)} className="h-4 w-4 accent-red-600" /><AlertTriangle size={18} className={item.has_issue ? 'text-red-600' : 'text-slate-400'} />Có issue / blocker</label><label className="ml-auto flex items-center gap-3 text-sm font-semibold">Tiến độ <input type="number" min="0" max="100" value={item.progress_percent ?? ''} onChange={(event) => update(index, 'progress_percent', event.target.value === '' ? null : Number(event.target.value))} className="field w-24" />%</label>{item.has_issue && <textarea className="field w-full border-red-200 bg-white" value={item.issue_description ?? ''} onChange={(event) => update(index, 'issue_description', event.target.value)} placeholder="Mô tả blocker và hỗ trợ bạn cần..." />}</div>
              </div>
            </section>
          ))}
        </div>
        <button type="button" className="btn-secondary mt-4" onClick={() => { setItems((current) => [...current, blank()]); setDirty(true); }}><Plus size={18} />Thêm công việc</button>
        <section className="card mt-6 p-5"><label className="label">Ghi chú chung</label><textarea className="field min-h-24" value={note} onChange={(event) => { setNote(event.target.value); setDirty(true); }} placeholder="Thông tin chung cần team lưu ý..." /></section>
      </fieldset>
      <div className="sticky bottom-4 mt-6 flex justify-end gap-3 rounded-2xl border border-stone-200 bg-white/90 p-4 shadow-xl backdrop-blur"><button className="btn-secondary" onClick={save} disabled={saving || locked}><Save size={18} />Lưu nháp</button><button className="btn-primary" onClick={submit} disabled={saving || locked || date > today()}><Send size={18} />Submit Daily</button></div>
    </div>
  );
}
