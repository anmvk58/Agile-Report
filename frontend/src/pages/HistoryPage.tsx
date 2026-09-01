import {useEffect, useState} from 'react';
import {CalendarCheck, ChevronDown} from 'lucide-react';
import {api} from '../api/client';
import {DateRangeFilter, rangeForPreset, type DateRange} from '../components/DateRangeFilter';
import {Empty, Loading, StatusBadge} from '../components/ui';
import type {Daily} from '../types';

export function HistoryPage() {
  const [items, setItems] = useState<Daily[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState<number | null>(null);
  const [range, setRange] = useState<DateRange>(() => rangeForPreset('week'));

  useEffect(() => {
    if (!range.from || !range.to || range.from > range.to) return;
    setLoading(true);
    const params = new URLSearchParams({date_from: range.from, date_to: range.to});
    api<Daily[]>(`/daily-reports/me?${params}`).then(setItems).finally(() => setLoading(false));
  }, [range.from, range.to]);

  return (
    <div>
      <div className="mb-7">
        <p className="mb-1 text-sm font-bold uppercase tracking-widest text-brand">Nhật ký công việc</p>
        <h1 className="text-3xl font-extrabold">Lịch sử Daily</h1>
      </div>
      <div className="card mb-5 p-4"><DateRangeFilter value={range} onChange={setRange} initialPreset="week" /></div>
      {loading ? <Loading /> : items.length === 0 ? (
        <Empty title="Chưa có Daily" detail="Không có báo cáo trong khoảng thời gian đã chọn." />
      ) : (
        <div className="space-y-3">
          {items.map((report) => (
            <div key={report.id} className="card overflow-hidden">
              <button className="flex w-full items-center gap-4 p-5 text-left" onClick={() => setOpen(open === report.id ? null : report.id)}>
                <div className="rounded-xl bg-orange-50 p-3 text-brand"><CalendarCheck /></div>
                <div className="flex-1">
                  <div className="font-bold">{new Date(`${report.report_date}T00:00:00`).toLocaleDateString('vi-VN', {weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric'})}</div>
                  <div className="text-sm text-slate-500">{report.items.length} công việc · Cập nhật {new Date(report.updated_at).toLocaleTimeString('vi-VN', {hour: '2-digit', minute: '2-digit'})}</div>
                </div>
                <StatusBadge status={report.status} />
                <ChevronDown className={`transition ${open === report.id ? 'rotate-180' : ''}`} />
              </button>
              {open === report.id && (
                <div className="border-t border-stone-200 bg-stone-50 p-5">
                  <div className="space-y-4">
                    {report.items.map((item, index) => (
                      <div key={item.id ?? index} className="rounded-xl bg-white p-4">
                        <div className="font-bold">{item.story_code && <span className="mr-2 text-brand">{item.story_code}</span>}{item.task_title}</div>
                        <div className="mt-3 grid gap-3 text-sm md:grid-cols-2"><p><b>Đã làm:</b> {item.yesterday_work || '—'}</p><p><b>Kế hoạch:</b> {item.today_plan || '—'}</p></div>
                        {item.has_issue && <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700"><b>Blocker:</b> {item.issue_description}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
