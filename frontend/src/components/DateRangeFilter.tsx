import React from 'react';
import {CalendarDays} from 'lucide-react';

export type DateRange = {from: string; to: string};
export type DatePreset = 'today' | 'yesterday' | 'week' | 'custom';

const formatDate = (value: Date) =>
  new Intl.DateTimeFormat('en-CA', {timeZone: 'Asia/Ho_Chi_Minh'}).format(value);

const addDays = (isoDate: string, amount: number) => {
  const [year, month, day] = isoDate.split('-').map(Number);
  const value = new Date(Date.UTC(year, month - 1, day));
  value.setUTCDate(value.getUTCDate() + amount);
  return value.toISOString().slice(0, 10);
};

export function rangeForPreset(preset: Exclude<DatePreset, 'custom'>): DateRange {
  const today = formatDate(new Date());
  if (preset === 'yesterday') {
    const yesterday = addDays(today, -1);
    return {from: yesterday, to: yesterday};
  }
  if (preset === 'week') {
    const [year, month, day] = today.split('-').map(Number);
    const weekday = new Date(Date.UTC(year, month - 1, day)).getUTCDay();
    return {from: addDays(today, -((weekday + 6) % 7)), to: today};
  }
  return {from: today, to: today};
}

export function DateRangeFilter({value, onChange, initialPreset = 'today'}: {
  value: DateRange;
  onChange: (range: DateRange) => void;
  initialPreset?: DatePreset;
}) {
  const [preset, setPreset] = React.useState<DatePreset>(initialPreset);
  const options: {value: DatePreset; label: string}[] = [
    {value: 'today', label: 'Hôm nay'},
    {value: 'yesterday', label: 'Hôm qua'},
    {value: 'week', label: 'Tuần này'},
    {value: 'custom', label: 'Khác'},
  ];

  const selectPreset = (next: DatePreset) => {
    setPreset(next);
    if (next !== 'custom') onChange(rangeForPreset(next));
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex flex-wrap gap-2" aria-label="Chọn nhanh khoảng thời gian">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            aria-pressed={preset === option.value}
            className={`rounded-xl border px-4 py-2 text-sm font-semibold transition ${preset === option.value ? 'border-navy bg-navy text-white shadow-sm' : 'border-stone-200 bg-white text-slate-600 hover:border-orange-300 hover:text-brand'}`}
            onClick={() => selectPreset(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
      {preset === 'custom' && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-orange-200 bg-orange-50/60 p-2">
          <CalendarDays size={18} className="ml-1 text-brand" />
          <label className="flex items-center gap-2 text-sm font-semibold">Từ<input className="field w-auto bg-white" type="date" max={value.to} value={value.from} onChange={(event) => onChange({from: event.target.value, to: value.to})} /></label>
          <label className="flex items-center gap-2 text-sm font-semibold">Đến<input className="field w-auto bg-white" type="date" min={value.from} value={value.to} onChange={(event) => onChange({from: value.from, to: event.target.value})} /></label>
        </div>
      )}
    </div>
  );
}
