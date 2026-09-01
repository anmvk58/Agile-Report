import {useEffect, useState} from 'react';
import {AlertTriangle, BookOpenCheck, CalendarDays, Download, Eye, EyeOff, FileCheck2, Lock, UserRound} from 'lucide-react';
import {api, download} from '../api/client';
import {DateRangeFilter, rangeForPreset, type DateRange} from '../components/DateRangeFilter';
import {Empty, StatusBadge, Toast, type ToastData} from '../components/ui';
import type {Page} from '../types';

type TaskDetail = {date: string; task_title: string; completed?: string; today_plan?: string; progress_percent: number | null; has_issue: boolean; issue_description?: string};
type MemberStory = {story_id: number; code: string; title: string; tasks: TaskDetail[]};
type MemberSummary = {full_name: string; story_details?: MemberStory[]; submitted_days: number; missing_days: number};
type WeeklySnapshot = {period: {start: string; end: string}; options?: {include_next_plans: boolean}; by_member: MemberSummary[]; by_story: unknown[]};
type Weekly = {id: number; week_start: string; week_end: string; status: string; snapshot: WeeklySnapshot};

const formatDate = (value: string) => new Date(`${value}T00:00:00`).toLocaleDateString('vi-VN', {weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric'});

export function WeeklyPage() {
  const [range, setRange] = useState<DateRange>(() => rangeForPreset('week'));
  const [preview, setPreview] = useState<WeeklySnapshot | null>(null);
  const [reports, setReports] = useState<Weekly[]>([]);
  const [toast, setToast] = useState<ToastData>(null);
  const [showNextPlans, setShowNextPlans] = useState(false);
  const load = () => api<Page<Weekly>>('/weekly-reports').then((result) => setReports(result.items));
  useEffect(() => { load(); }, []);

  const showPreview = async () => {
    try { setPreview(await api('/weekly-reports/preview', {method: 'POST', body: JSON.stringify({week_start: range.from, week_end: range.to, include_next_plans: showNextPlans})})); }
    catch (error) { setToast({kind: 'error', message: error instanceof Error ? error.message : 'Không thể xem trước'}); }
  };
  const generate = async () => {
    try { await api('/weekly-reports/generate', {method: 'POST', body: JSON.stringify({week_start: range.from, week_end: range.to, include_next_plans: showNextPlans})}); setToast({kind: 'success', message: 'Đã tạo báo cáo'}); load(); }
    catch (error) { setToast({kind: 'error', message: error instanceof Error ? error.message : 'Không thể tạo'}); }
  };
  const finalize = async (id: number) => {
    if (!confirm('Sau khi chốt, snapshot báo cáo sẽ được giữ nguyên. Tiếp tục?')) return;
    await api(`/weekly-reports/${id}/finalize`, {method: 'POST'}); load();
  };

  return (
    <div>
      <Toast toast={toast} clear={() => setToast(null)} />
      <div className="mb-7"><p className="mb-1 text-sm font-bold uppercase tracking-widest text-brand">Tổng hợp tự động</p><h1 className="text-3xl font-extrabold">Báo cáo tuần</h1></div>
      <section className="card mb-6 p-5"><DateRangeFilter value={range} onChange={(next) => { setRange(next); setPreview(null); }} initialPreset="week" /><div className="mt-4 flex flex-wrap gap-3"><button className={`btn-secondary ${!showNextPlans ? 'border-orange-300 bg-orange-50 text-brand' : ''}`} onClick={() => setShowNextPlans((current) => !current)}>{showNextPlans ? <EyeOff size={18} /> : <Eye size={18} />}{showNextPlans ? 'Ẩn kế hoạch tiếp theo' : 'Hiện kế hoạch tiếp theo'}</button><button className="btn-secondary" onClick={showPreview}>Xem trước</button><button className="btn-primary" onClick={generate}><FileCheck2 size={18} />Tạo báo cáo</button></div></section>

      {preview && (
        <section className="card mb-7 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-2xl font-extrabold">Bản xem trước</h2><p className="mt-1 text-sm text-slate-500">{formatDate(preview.period.start)} – {formatDate(preview.period.end)}</p></div><span className="badge bg-orange-50 text-brand">Cây công việc theo thành viên</span></div>
          <div className="mt-7 space-y-6">
            {preview.by_member.map((member) => (
              <article className="overflow-hidden rounded-2xl border border-stone-200" key={member.full_name}>
                <div className="flex flex-wrap items-center gap-3 bg-navy px-5 py-4 text-white"><div className="grid h-9 w-9 place-items-center rounded-xl bg-white/10"><UserRound size={20} /></div><div className="flex-1"><p className="text-xs font-bold uppercase tracking-wider text-orange-300">Thành viên</p><h3 className="text-lg font-extrabold">{member.full_name}</h3></div><span className="text-xs font-semibold text-slate-200">{member.submitted_days} Daily · {member.missing_days} thiếu</span></div>
                {(member.story_details ?? []).length === 0 ? <p className="p-5 text-sm text-slate-500">Không có công việc gắn với User Story trong kỳ này.</p> : (
                  <div className="space-y-5 p-5">
                    {(member.story_details ?? []).map((story) => (
                      <section className="relative ml-3 border-l-2 border-orange-200 pl-6" key={story.story_id}>
                        <span className="absolute -left-2 top-1 h-3.5 w-3.5 rounded-full border-4 border-white bg-orange-500" />
                        <div className="flex flex-wrap items-center gap-2"><BookOpenCheck size={18} className="text-brand" /><span className="badge bg-orange-50 text-brand">LV1 · {story.code}</span><h4 className="font-extrabold text-navy">{story.title}</h4></div>
                        <div className="mt-4 space-y-3">
                          {story.tasks.map((task, index) => (
                            <div className="relative ml-2 rounded-xl border border-stone-200 bg-stone-50 p-4" key={`${task.date}-${task.task_title}-${index}`}>
                              <div className="flex flex-wrap items-start justify-between gap-2"><div><p className="text-xs font-bold uppercase tracking-wide text-brand">LV2 · Task</p><h5 className="mt-1 font-extrabold">{task.task_title}</h5></div><div className="flex items-center gap-2 text-xs font-semibold text-slate-500"><CalendarDays size={15} />{formatDate(task.date)}{task.progress_percent !== null && <span className="badge bg-white text-brand">{task.progress_percent}%</span>}</div></div>
                              <div className="mt-3 rounded-xl bg-white p-3 text-sm"><p className="mb-1 font-bold text-emerald-700">Daily hoàn thành</p><p className="text-slate-700">{task.completed || '—'}</p></div>
                              {showNextPlans && task.today_plan && <div className="mt-2 rounded-xl bg-blue-50 p-3 text-sm"><p className="mb-1 font-bold text-blue-700">Kế hoạch tiếp theo</p><p className="text-slate-700">{task.today_plan}</p></div>}
                              {task.has_issue && <p className="mt-2 flex gap-2 rounded-xl bg-red-50 p-3 text-sm font-medium text-red-700"><AlertTriangle size={17} className="shrink-0" />{task.issue_description || 'Có blocker'}</p>}
                            </div>
                          ))}
                        </div>
                      </section>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      )}

      <h2 className="mb-4 text-xl font-bold">Báo cáo đã tạo</h2>
      {reports.length === 0 ? <Empty title="Chưa có báo cáo" detail="Chọn khoảng thời gian và tạo báo cáo đầu tiên." /> : <div className="space-y-3">{reports.map((report) => <div className="card flex flex-wrap items-center gap-4 p-5" key={report.id}><div className="flex-1"><div className="font-bold">Kỳ {new Date(report.week_start).toLocaleDateString('vi-VN')} – {new Date(report.week_end).toLocaleDateString('vi-VN')}</div><div className="mt-1 text-sm text-slate-500">{report.snapshot.by_member.length} thành viên · {report.snapshot.by_story.length} User Story</div></div><StatusBadge status={report.status} />{report.status !== 'FINALIZED' && <button className="btn-secondary" onClick={() => finalize(report.id)}><Lock size={16} />Chốt</button>}<button className="btn-secondary" onClick={() => download(`/weekly-reports/${report.id}/export?format=markdown`, `weekly-${report.week_start}.md`)}><Download size={16} />Markdown</button><button className="btn-secondary" onClick={() => download(`/weekly-reports/${report.id}/export?format=csv`, `weekly-${report.week_start}.csv`)}>CSV</button></div>)}</div>}
    </div>
  );
}
