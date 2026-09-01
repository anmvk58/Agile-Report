import {useEffect, useMemo, useState} from 'react';
import {AlertTriangle, History, RotateCcw} from 'lucide-react';
import {api} from '../api/client';
import {DateRangeFilter, rangeForPreset, type DateRange} from '../components/DateRangeFilter';
import {Empty, Loading, Modal, StatusBadge, Toast, type ToastData} from '../components/ui';
import type {Daily, User} from '../types';

type TeamDailyRow = {report_date: string; user: User; report: Daily | null};
type ReopenAudit = {id: number; reason: string; reopened_at: string; reopened_by: number; reopened_by_name: string};

const displayDate = (value: string) => new Date(`${value}T00:00:00`).toLocaleDateString('vi-VN', {
  weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric',
});
const today = () => new Intl.DateTimeFormat('en-CA', {timeZone: 'Asia/Ho_Chi_Minh'}).format(new Date());

export function TeamDaily() {
  const [range, setRange] = useState<DateRange>(() => rangeForPreset('today'));
  const [rows, setRows] = useState<TeamDailyRow[]>([]);
  const [issues, setIssues] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<TeamDailyRow | null>(null);
  const [history, setHistory] = useState<ReopenAudit[]>([]);
  const [reason, setReason] = useState('');
  const [reopening, setReopening] = useState(false);
  const [toast, setToast] = useState<ToastData>(null);

  const load = () => {
    if (!range.from || !range.to || range.from > range.to) return;
    setLoading(true);
    const params = new URLSearchParams({date_from: range.from, date_to: range.to, issues_only: String(issues)});
    api<TeamDailyRow[]>(`/admin/daily-reports?${params}`).then(setRows).finally(() => setLoading(false));
  };
  useEffect(load, [range.from, range.to, issues]);

  const showReopen = async (row: TeamDailyRow) => {
    if (!row.report) return;
    setSelected(row); setReason('');
    try { setHistory(await api<ReopenAudit[]>(`/admin/daily-reports/${row.report.id}/reopen-history`)); }
    catch { setHistory([]); }
  };
  const reopen = async () => {
    if (!selected?.report || reason.trim().length < 3) return;
    setReopening(true);
    try {
      await api(`/admin/daily-reports/${selected.report.id}/reopen`, {method: 'POST', body: JSON.stringify({reason})});
      setToast({kind: 'success', message: `Đã mở lại Daily của ${selected.user.full_name}`});
      setSelected(null); load();
    } catch (error) { setToast({kind: 'error', message: error instanceof Error ? error.message : 'Không thể mở lại Daily'}); }
    finally { setReopening(false); }
  };

  const groups = useMemo(() => {
    const grouped = new Map<string, TeamDailyRow[]>();
    rows.forEach((row) => grouped.set(row.report_date, [...(grouped.get(row.report_date) ?? []), row]));
    return [...grouped.entries()].sort(([left], [right]) => right.localeCompare(left));
  }, [rows]);

  return (
    <div>
      <Toast toast={toast} clear={() => setToast(null)} />
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-sm font-bold uppercase tracking-widest text-brand">Nhịp làm việc của team</p>
          <h1 className="text-3xl font-extrabold">Daily của team</h1>
        </div>
        <label className="flex items-center gap-2 rounded-xl border bg-white px-3 py-2 text-sm font-semibold">
          <input type="checkbox" checked={issues} onChange={(event) => setIssues(event.target.checked)} />
          Chỉ hiện blocker
        </label>
      </div>
      <div className="card mb-5 p-4"><DateRangeFilter value={range} onChange={setRange} /></div>

      {loading ? <Loading /> : groups.length === 0 ? (
        <Empty title="Không có Daily" detail={issues ? 'Không có blocker trong khoảng thời gian đã chọn.' : 'Không có dữ liệu trong khoảng thời gian đã chọn.'} />
      ) : (
        <div className="space-y-7">
          {groups.map(([reportDate, dateRows]) => (
            <section key={reportDate}>
              <h2 className="mb-3 text-lg font-extrabold capitalize text-navy">{displayDate(reportDate)}</h2>
              <div className="space-y-4">
                {dateRows.map((row) => (
                  <article className="card overflow-hidden" key={`${reportDate}-${row.user.id}`}>
                    <div className="flex items-center gap-3 border-b border-stone-200 px-5 py-4">
                      <div className="grid h-10 w-10 place-items-center rounded-full bg-navy font-bold text-white">{row.user.full_name[0]}</div>
                      <div className="flex-1"><div className="font-bold">{row.user.full_name}</div><div className="text-xs text-slate-500">@{row.user.username}</div></div>
                      {row.report?.is_reopened && <span className="badge bg-amber-100 text-amber-800">Đã mở lại</span>}
                      {row.report ? <StatusBadge status={row.report.status} /> : <span className="badge bg-stone-100 text-stone-500">Chưa khai báo</span>}
                      {row.report && reportDate < today() && (
                        <button className="btn-secondary px-3 py-2" onClick={() => showReopen(row)}>
                          {!row.report.is_reopened ? <><RotateCcw size={16} />Mở lại</> : <><History size={16} />Lịch sử mở lại</>}
                        </button>
                      )}
                    </div>
                    {row.report && (
                      <div className="grid gap-3 p-5 lg:grid-cols-2">
                        {row.report.items.map((item, index) => (
                          <div className={`rounded-xl border p-4 ${item.has_issue ? 'border-red-200 bg-red-50/50' : 'border-stone-200'}`} key={item.id ?? index}>
                            {(item.story_code || item.story_title) && (
                              <div className="mb-2 flex flex-wrap items-center gap-2">
                                {item.story_code && <span className="badge bg-orange-50 text-brand">{item.story_code}</span>}
                                {item.story_title && <span className="text-sm font-semibold text-brand">{item.story_title}</span>}
                              </div>
                            )}
                            <div className="font-bold">{item.task_title}</div>
                            <p className="mt-2 text-sm text-slate-600"><b>Đã làm:</b> {item.yesterday_work || '—'}</p>
                            <p className="mt-1 text-sm text-slate-600"><b>Hôm nay:</b> {item.today_plan || '—'}</p>
                            {item.has_issue && <p className="mt-3 flex gap-2 text-sm font-medium text-red-700"><AlertTriangle size={17} />{item.issue_description}</p>}
                          </div>
                        ))}
                      </div>
                    )}
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
      {selected?.report && (
        <Modal title={`Mở lại Daily · ${selected.user.full_name}`} onClose={() => setSelected(null)}>
          {!selected.report.is_reopened ? (
            <div>
              <label className="label">Lý do mở lại <span className="text-brand">*</span></label>
              <textarea className="field min-h-24" maxLength={500} value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Ví dụ: Thành viên nhập nhầm nội dung task..." />
              <div className="mt-4 flex justify-end gap-3"><button className="btn-secondary" onClick={() => setSelected(null)}>Hủy</button><button className="btn-primary" disabled={reopening || reason.trim().length < 3} onClick={reopen}><RotateCcw size={17} />{reopening ? 'Đang mở...' : 'Xác nhận mở lại'}</button></div>
            </div>
          ) : <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-800">Daily đang được mở để thành viên chỉnh sửa. Báo cáo sẽ tự khóa sau khi submit lại.</p>}
          <div className="mt-6 border-t border-stone-200 pt-5">
            <h3 className="font-bold">Lịch sử mở lại</h3>
            {history.length === 0 ? <p className="mt-2 text-sm text-slate-500">Chưa có lần mở lại nào.</p> : <div className="mt-3 space-y-3">{history.map((audit) => <div key={audit.id} className="rounded-xl bg-stone-50 p-3 text-sm"><div className="font-semibold">{audit.reopened_by_name} · {new Date(audit.reopened_at).toLocaleString('vi-VN')}</div><p className="mt-1 text-slate-600">{audit.reason}</p></div>)}</div>}
          </div>
        </Modal>
      )}
    </div>
  );
}
