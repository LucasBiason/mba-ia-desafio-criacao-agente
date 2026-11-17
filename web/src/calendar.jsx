import React, { useLayoutEffect, useRef, useState, useSyncExternalStore } from 'react';
import './styles/calendar.css';

const firstMonth = '0001-01';
const lastMonth = '9999-12';
const compactQuery = '(max-width: 680px)';
const dayInMilliseconds = 86_400_000;

export function localToday(date = new Date()) {
  return [
    String(date.getFullYear()).padStart(4, '0'),
    String(date.getMonth() + 1).padStart(2, '0'),
    String(date.getDate()).padStart(2, '0'),
  ].join('-');
}

function civilDate(date) {
  return new Date(`${date}T00:00:00Z`);
}

function isoDate(date) {
  return date.getUTCFullYear() >= 1 && date.getUTCFullYear() <= 9999
    ? date.toISOString().slice(0, 10)
    : null;
}

function moveDays(date, amount) {
  return isoDate(new Date(civilDate(date).getTime() + amount * dayInMilliseconds));
}

function moveMonths(month, amount) {
  const date = civilDate(`${month}-01`);
  date.setUTCMonth(date.getUTCMonth() + amount);
  return isoDate(date)?.slice(0, 7);
}

function dateInMonth(month, day) {
  const end = new Date(civilDate(`${month}-01`));
  end.setUTCMonth(end.getUTCMonth() + 1, 0);
  return `${month}-${String(Math.min(day, end.getUTCDate())).padStart(2, '0')}`;
}

function getWeeks(month) {
  const firstDay = civilDate(`${month}-01`);
  const offset = firstDay.getUTCDay();
  const daysInMonth = Number(dateInMonth(month, 31).slice(-2));
  const weekCount = Math.max(5, Math.ceil((offset + daysInMonth) / 7));
  return Array.from({ length: weekCount }, (_, week) =>
    Array.from({ length: 7 }, (_, weekday) => {
      const difference = week * 7 + weekday - offset;
      return isoDate(new Date(firstDay.getTime() + difference * dayInMilliseconds));
    }),
  );
}

function subscribeToCompactView(callback) {
  const media = window.matchMedia(compactQuery);
  media.addEventListener('change', callback);
  return () => media.removeEventListener('change', callback);
}

function isCompactView() {
  return window.matchMedia(compactQuery).matches;
}

function CalendarToolbar({ month, monthLabel, onMonthChange, onToday }) {
  const picker = useRef(null);

  function changeMonth(nextMonth) {
    picker.current.open = false;
    onMonthChange(nextMonth);
  }

  function chooseMonth(event) {
    const nextMonth = event.target.value;
    if (/^(?!0000)\d{4}-(?:0[1-9]|1[0-2])$/.test(nextMonth) && event.target.validity.valid) {
      picker.current.querySelector('summary').focus();
      changeMonth(nextMonth);
    }
  }

  return (
    <div className="month-calendar__toolbar">
      <div className="month-calendar__navigation">
        <button className="month-calendar__today" type="button" onClick={() => {
          picker.current.open = false;
          onToday();
        }}>Hoje</button>
        <button
          className="month-calendar__arrow"
          type="button"
          aria-label="Mês anterior"
          disabled={month === firstMonth}
          onClick={() => changeMonth(moveMonths(month, -1))}
        >
          <span aria-hidden="true" />
        </button>
        <button
          className="month-calendar__arrow month-calendar__arrow--next"
          type="button"
          aria-label="Próximo mês"
          disabled={month === lastMonth}
          onClick={() => changeMonth(moveMonths(month, 1))}
        >
          <span aria-hidden="true" />
        </button>
        <details className="month-calendar__jump" ref={picker} onBlur={event => {
          if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget)) event.currentTarget.open = false;
        }} onKeyDown={event => {
          if (event.key === 'Escape' && event.currentTarget.open) {
            event.currentTarget.open = false;
            event.currentTarget.querySelector('summary')?.focus();
          }
        }}>
          <summary aria-label="Ir para mês" title="Ir para mês">
            <span aria-hidden="true" />
          </summary>
          <div className="month-calendar__jump-panel">
            <label>
              Mês
              <input type="month" value={month} min={firstMonth} max={lastMonth} onChange={chooseMonth} />
            </label>
          </div>
        </details>
      </div>
      <h2 className="month-calendar__month" aria-live="polite">{monthLabel}</h2>
    </div>
  );
}

export function MonthCalendar({
  month,
  events = [],
  selectedDate,
  highlightedEventId,
  onMonthChange,
  onDateSelect,
  onEventSelect,
  onToday,
  today = localToday(),
  maxVisibleEvents = 3,
  locale = 'pt-BR',
}) {
  const compact = useSyncExternalStore(subscribeToCompactView, isCompactView, () => false);
  const [focusDate, setFocusDate] = useState(null);
  const pendingFocus = useRef(null);
  const dayButtons = useRef(new Map());
  const weeks = getWeeks(month);
  const activeDate = [focusDate, selectedDate, today].find(date => date?.startsWith(`${month}-`))
    ?? `${month}-01`;
  const eventsByDate = new Map();
  for (const event of events) {
    if (!eventsByDate.has(event.date)) eventsByDate.set(event.date, []);
    eventsByDate.get(event.date).push(event);
  }
  const visibleEventLimit = compact ? Math.min(maxVisibleEvents, 1) : maxVisibleEvents;
  const monthLabel = civilDate(`${month}-01`).toLocaleDateString(locale, {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
  const weekdayShort = new Intl.DateTimeFormat(locale, { weekday: 'short', timeZone: 'UTC' });
  const weekdayLong = new Intl.DateTimeFormat(locale, { weekday: 'long', timeZone: 'UTC' });
  const dateLabel = new Intl.DateTimeFormat(locale, { dateStyle: 'full', timeZone: 'UTC' });

  useLayoutEffect(() => {
    const target = dayButtons.current.get(pendingFocus.current);
    if (target) {
      pendingFocus.current = null;
      target.focus();
    }
  }, [focusDate, month]);

  function pressDateKey(keyboardEvent, date) {
    if (keyboardEvent.target !== keyboardEvent.currentTarget) return;

    const weekday = civilDate(date).getUTCDay();
    const daySteps = {
      ArrowLeft: -1,
      ArrowRight: 1,
      ArrowUp: -7,
      ArrowDown: 7,
      Home: -weekday,
      End: 6 - weekday,
    };
    let nextDate;
    if (Object.hasOwn(daySteps, keyboardEvent.key)) {
      nextDate = moveDays(date, daySteps[keyboardEvent.key]);
    } else if (keyboardEvent.key === 'PageUp' || keyboardEvent.key === 'PageDown') {
      const nextMonth = moveMonths(date.slice(0, 7), keyboardEvent.key === 'PageUp' ? -1 : 1);
      if (nextMonth) nextDate = dateInMonth(nextMonth, Number(date.slice(-2)));
    } else {
      return;
    }

    keyboardEvent.preventDefault();
    if (!nextDate || nextDate === date) return;
    pendingFocus.current = nextDate;
    setFocusDate(nextDate);
    const nextMonth = nextDate.slice(0, 7);
    if (nextMonth !== month) {
      onMonthChange(nextMonth);
    }
  }

  function selectDate(date) {
    setFocusDate(date);
    onDateSelect(date);
  }

  function jumpToToday() {
    setFocusDate(today);
    if (onToday) {
      onToday(today);
    } else if (today.startsWith(`${month}-`)) {
      onDateSelect(today);
    } else {
      pendingFocus.current = today;
      onMonthChange(today.slice(0, 7));
    }
  }

  function renderDate(date, weekday) {
    if (!date) return <div className="month-calendar__cell" role="gridcell" key={weekday} />;

    const dayEvents = eventsByDate.get(date) ?? [];
    const visibleEvents = dayEvents.slice(0, visibleEventLimit);
    if (visibleEventLimit > 0 && dayEvents.length > visibleEventLimit) {
      const highlighted = dayEvents.find(event => event.id === highlightedEventId);
      if (highlighted && !visibleEvents.includes(highlighted)) {
        visibleEvents[visibleEvents.length - 1] = highlighted;
      }
    }
    const extraEvents = dayEvents.length - visibleEvents.length;
    const accessibleDate = dateLabel.format(civilDate(date));
    const selected = date === selectedDate;
    const tabbable = date === activeDate;

    return (
      <div
        className="month-calendar__cell"
        role="gridcell"
        aria-selected={selected}
        data-adjacent={!date.startsWith(`${month}-`)}
        data-selected={selected}
        key={date}
      >
        <button
          className="month-calendar__day"
          type="button"
          aria-label={accessibleDate}
          aria-current={date === today ? 'date' : undefined}
          tabIndex={tabbable ? 0 : -1}
          ref={node => {
            if (node) dayButtons.current.set(date, node);
            else dayButtons.current.delete(date);
          }}
          onFocus={() => setFocusDate(date)}
          onKeyDown={keyboardEvent => pressDateKey(keyboardEvent, date)}
          onClick={() => selectDate(date)}
        >
          <span>{Number(date.slice(-2))}</span>
        </button>
        {visibleEvents.map(event => {
          const label = [event.time, event.title, event.subtitle].filter(Boolean).join(' · ');
          const highlighted = event.id === highlightedEventId;
          return (
            <button
              className="month-calendar__event"
              type="button"
              tabIndex={tabbable ? 0 : -1}
              data-tone={event.tone}
              data-highlighted={highlighted}
              aria-label={label}
              aria-pressed={highlighted}
              title={label}
              key={event.id}
              onFocus={() => setFocusDate(date)}
              onClick={() => onEventSelect ? onEventSelect(event) : selectDate(date)}
            >
              {event.time && <span className="month-calendar__event-time">{event.time}</span>}
              <span className="month-calendar__event-title">{event.title}</span>
            </button>
          );
        })}
        {extraEvents > 0 && (
          <button
            className="month-calendar__more"
            type="button"
            tabIndex={tabbable ? 0 : -1}
            aria-label={`Ver mais ${extraEvents} ${extraEvents === 1 ? 'evento' : 'eventos'} em ${accessibleDate}`}
            onFocus={() => setFocusDate(date)}
            onClick={() => selectDate(date)}
          >
            +{extraEvents}
          </button>
        )}
      </div>
    );
  }

  return (
    <section className="month-calendar">
      <CalendarToolbar
        month={month}
        monthLabel={monthLabel}
        onMonthChange={onMonthChange}
        onToday={jumpToToday}
      />
      <div className="month-calendar__grid" role="grid" aria-label={monthLabel}>
        <div className="month-calendar__weekdays" role="row">
          {Array.from({ length: 7 }, (_, weekday) => {
            const date = new Date(Date.UTC(2024, 0, 7 + weekday));
            const label = weekdayLong.format(date);
            return (
              <div className="month-calendar__weekday" role="columnheader" aria-label={label} key={weekday}>
                {weekdayShort.format(date).replace(/\.$/, '')}
              </div>
            );
          })}
        </div>
        {weeks.map((week, index) => (
          <div className="month-calendar__week" role="row" key={index}>
            {week.map(renderDate)}
          </div>
        ))}
      </div>
    </section>
  );
}
