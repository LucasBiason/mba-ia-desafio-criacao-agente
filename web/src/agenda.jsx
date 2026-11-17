import { useEffect, useRef, useState } from "react";
import { useQuery } from "./api";
import { MonthCalendar, localToday } from "./calendar";
import { HoursEditor, hourLabel, reservationHours } from "./hours";
import { Button, Empty, Feedback, Field, PageHeading, QueryResult, Tag, money, shortDate } from "./ui";
import "./styles/agenda.css";

const tones = ["green", "blue", "amber", "purple"];
const weekday = new Intl.DateTimeFormat("pt-BR", { weekday: "long", timeZone: "UTC" });
const testReservation = item => item.code.startsWith("TEST-AGENDA-");

function ReservationDay({ area, date, rows, highlightedCode, residentName, areaTone, onClose, onSaveHours }) {
  const dialog = useRef(null);
  const [editing, setEditing] = useState(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!dialog.current.open) dialog.current.showModal();
  }, []);

  async function saveHours(body) {
    await onSaveHours(editing.code, body);
    setEditing(null);
    setNotice("Horários da reserva atualizados.");
  }

  return <dialog className="agenda-day-dialog" ref={dialog} onClose={onClose} aria-labelledby="agenda-day-title"
    onClick={event => { if (event.target === event.currentTarget) dialog.current.close(); }}>
    <div className="agenda-day-content">
      <header className="agenda-day-header">
        <div>
          <p>{weekday.format(new Date(date + "T00:00:00Z"))} · {area}</p>
          <h2 id="agenda-day-title">Reservas de {shortDate(date)}</h2>
        </div>
        <button type="button" className="agenda-close" aria-label="Fechar reservas do dia"
          onClick={() => dialog.current.close()}>×</button>
      </header>
      {editing && <HoursEditor title={"Horários da reserva " + editing.code} fields={reservationHours}
        row={editing} onSave={saveHours} onCancel={() => setEditing(null)} />}
      <Feedback message={notice} variant="success" />
      {rows.length ? <ul className="agenda-reservation-list">
        {rows.map(item => <li key={item.code} className="agenda-reservation"
          data-tone={item.status === "active" ? areaTone(item.area_id) : "neutral"}
          data-highlighted={item.code === highlightedCode}>
          <div className="agenda-reservation-title">
            <strong>{item.area_name}</strong>
            <Tag tone={item.status === "active" ? "positive" : "neutral"}>
              {item.status === "active" ? "Ativa" : "Cancelada"}
            </Tag>
          </div>
          <p>{residentName(item)} · Apto {item.apartment}</p>
          <dl className="agenda-reservation-data">
            <div><dt>Início</dt><dd>{hourLabel(item.start_time)}</dd></div>
            <div><dt>Fim</dt><dd>{hourLabel(item.end_time)}</dd></div>
            <div><dt>Taxa</dt><dd>{money(item.fee_cents)}</dd></div>
          </dl>
          <div className="agenda-reservation-footer">
            <span><strong>{item.code}</strong>{testReservation(item) && <> · Teste</>}</span>
            <Button size="small" variant="secondary" aria-label={"Editar horários da reserva " + item.code}
              onClick={() => { setNotice(""); setEditing(item); }}>Editar horários</Button>
          </div>
        </li>)}
      </ul> : <Empty title="Nenhuma reserva para este dia." />}
    </div>
  </dialog>;
}

function ReservationCalendar({ api, areas, reservations, users, refresh }) {
  const catalog = new Map(areas.map((area, index) =>
    [area.id, { name: area.name, tone: tones[index % tones.length] }]));
  const [selection, setSelection] = useState(() =>
    ({ areaId: "", month: localToday().slice(0, 7), date: "", code: "" }));
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [searchError, setSearchError] = useState("");

  const residents = new Map((users.data ?? []).map(person => [person.id, person.name]));
  const residentName = item => residents.get(item.resident_id) ?? "Morador não identificado";
  const areaTone = areaId => catalog.get(areaId)?.tone ?? "neutral";
  const areaRows = reservations.filter(item => !selection.areaId || item.area_id === selection.areaId)
    .sort((first, second) => first.date.localeCompare(second.date)
      || (first.start_time ?? "99:99").localeCompare(second.start_time ?? "99:99")
      || first.area_name.localeCompare(second.area_name, "pt-BR"));
  const events = areaRows.map(item => ({
    id: item.code,
    date: item.date,
    title: item.status === "active" ? residentName(item) : "Cancelada · " + residentName(item),
    subtitle: item.area_name + " · Apto " + item.apartment + " · " + item.code,
    time: item.start_time,
    tone: item.status === "active" ? areaTone(item.area_id) : "neutral",
  }));

  function openDay(date, eventId = "", areaId = selection.areaId) {
    setSelection({ areaId, month: date.slice(0, 7), date, code: eventId });
    setSearchError("");
    setOpen(true);
  }

  function moveMonth(month) {
    setSelection({ ...selection, month, date: "", code: "" });
    setSearchError("");
  }

  function locate(value, submitted = false) {
    setCode(value);
    const term = value.trim().toUpperCase();
    const match = term && reservations.find(item => item.code.toUpperCase() === term);
    if (match) {
      openDay(match.date, match.code, match.area_id);
      return;
    }
    if (selection.code) setSelection({ ...selection, code: "" });
    setSearchError(submitted && term ? "Nenhuma reserva encontrada com esse código." : "");
  }

  async function saveHours(reservationCode, body) {
    await api("/api/admin/reservations/" + encodeURIComponent(reservationCode) + "/hours", { method: "PATCH", body });
    refresh();
  }

  const dayRows = areaRows.filter(item => item.date === selection.date);

  return <div className="stack">
    {users.error && <Feedback message="Os nomes dos moradores estão temporariamente indisponíveis." variant="warning" />}
    {catalog.size ? <section className="agenda-surface" aria-label="Calendário de reservas">
      <div className="agenda-filters">
        <Field label="Área" id="calendar-area">
          <select id="calendar-area" value={selection.areaId} onChange={event => {
            setSelection({ ...selection, areaId: event.target.value, date: "", code: "" });
            setSearchError("");
          }}>
            <option value="">Todas as áreas</option>
            {[...catalog].map(([id, area]) => <option key={id} value={id}>{area.name}</option>)}
          </select>
        </Field>
        <form className="agenda-search" onSubmit={event => { event.preventDefault(); locate(code, true); }}>
          <label htmlFor="agenda-code">Código da reserva</label>
          <div>
            <input id="agenda-code" type="search" value={code} onChange={event => locate(event.target.value)} />
            <Button type="submit" variant="secondary">Localizar</Button>
          </div>
        </form>
      </div>
      {!selection.areaId && catalog.size > 1 && <ul className="agenda-area-key" aria-label="Cores das áreas">
        {[...catalog].map(([id, area]) => <li key={id} data-tone={area.tone}>{area.name}</li>)}
      </ul>}
      <Feedback message={searchError} variant="warning" />
      <MonthCalendar month={selection.month} events={events} selectedDate={selection.date} highlightedEventId={selection.code} maxVisibleEvents={2}
        onMonthChange={moveMonth} onToday={date => moveMonth(date.slice(0, 7))}
        onDateSelect={date => openDay(date)} onEventSelect={event => openDay(event.date, event.id)} />
    </section> : <Empty title="Nenhuma área cadastrada." />}
    {open && <ReservationDay key={selection.date} area={catalog.get(selection.areaId)?.name ?? "Todas as áreas"}
      date={selection.date} rows={dayRows} highlightedCode={selection.code} residentName={residentName}
      areaTone={areaTone} onClose={() => setOpen(false)} onSaveHours={saveHours} />}
  </div>;
}

export function Agenda({ api }) {
  const areas = useQuery(api, "/api/admin/areas");
  const reservations = useQuery(api, "/api/admin/reservations");
  const users = useQuery(api, "/api/admin/users");

  return <>
    <PageHeading title="Agenda" section="Administração" />
    <QueryResult query={areas}>{catalog =>
      <QueryResult query={reservations}>{items =>
        <ReservationCalendar api={api} areas={catalog} reservations={items} users={users} refresh={reservations.refresh} />
      }</QueryResult>
    }</QueryResult>
  </>;
}
