import { useEffect, useRef, useState } from "react";
import { HoursEditor, hourLabel, reservationHours, visitHours } from "./hours";
import {
  Button,
  Feedback,
  LinkButton,
  PageHeading,
  QueryResult,
  Table,
  Tag,
  money,
  shortDate,
} from "./ui";

const reservationColumns = [
  { title: "Código", render: (item) => <strong>{item.code}</strong> },
  { title: "Apartamento", render: (item) => item.apartment },
  { title: "Área comum", render: (item) => item.area_name ?? item.area_id },
  { title: "Data", render: (item) => shortDate(item.date) },
  ...reservationHours.map(({ key, label }) => ({
    title: label,
    render: (item) => hourLabel(item[key]),
  })),
  { title: "Taxa", render: (item) => money(item.fee_cents) },
  {
    title: "Situação",
    render: (item) =>
      item.status === "cancelled" ? (
        <Tag>Cancelada</Tag>
      ) : (
        <Tag tone="positive">Ativa</Tag>
      ),
  },
];

const visitColumns = [
  { title: "Visitante", render: (item) => <strong>{item.name}</strong> },
  { title: "Apartamento", render: (item) => item.apartment },
  { title: "Data da visita", render: (item) => shortDate(item.date) },
  ...visitHours.map(({ key, label }) => ({
    title: label,
    render: (item) => hourLabel(item[key]),
  })),
  { title: "Situação", render: () => <Tag tone="positive">Autorizada</Tag> },
];

function ReservationDetails({ item, close }) {
  const dialog = useRef(null);
  useEffect(() => {
    const element = dialog.current;
    if (!element.open) element.showModal();
    return () => {
      if (element.open) element.close();
    };
  }, []);
  return (
    <dialog
      className="panel reservation-details"
      ref={dialog}
      aria-labelledby="reservation-details-title"
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) close();
      }}
    >
      <div className="stack" onClick={(event) => event.stopPropagation()}>
        <h2 id="reservation-details-title">Detalhes da reserva</h2>
        <dl>
          {reservationColumns.map((column) => (
            <div key={column.title}>
              <dt>{column.title}</dt>
              <dd>{column.render(item)}</dd>
            </div>
          ))}
        </dl>
        <div className="actions">
          <Button variant="secondary" onClick={close}>
            Fechar detalhes
          </Button>
        </div>
      </div>
    </dialog>
  );
}

export function Records({ query, kind, resident, saveHours }) {
  const [search, setSearch] = useState("");
  const [date, setDate] = useState("");
  const [area, setArea] = useState("");
  const [editing, setEditing] = useState(null);
  const [notice, setNotice] = useState("");
  const [details, setDetails] = useState(null);
  const openDetails = resident && kind === "reservations";
  const reservation = kind === "reservations";
  const title = reservation
    ? resident
      ? "Minhas reservas"
      : "Agenda"
    : resident
      ? "Histórico de visitas"
      : "Autorizações de visita";
  const columns = reservation ? reservationColumns : visitColumns;
  const editableColumns = saveHours
    ? [
        ...columns,
        {
          title: "Ações",
          render: (item) => (
            <Button
              size="small"
              variant="secondary"
              aria-label={"Editar horários da visita de " + item.name}
              onClick={() => {
                setNotice("");
                setEditing(item);
              }}
            >
              Editar horários
            </Button>
          ),
        },
      ]
    : openDetails
      ? [
          ...columns,
          {
            title: "Detalhes",
            render: (item) => (
              <Button
                size="small"
                variant="secondary"
                aria-label={"Ver detalhes da reserva " + item.code}
                onClick={(event) => {
                  event.stopPropagation();
                  setDetails(item);
                }}
              >
                Ver detalhes
              </Button>
            ),
          },
        ]
      : columns;

  async function updateHours(body) {
    await saveHours(editing.id, body);
    setEditing(null);
    setNotice("Horários da visita atualizados.");
    query.refresh();
  }

  return (
    <>
      <PageHeading
        title={title}
        section={resident ? "Área do morador" : "Administração"}
      >
        {openDetails
          ? "Abra uma reserva para conferir área, status, taxa e horários."
          : reservation
            ? "Consulte os horários registrados nas áreas comuns."
            : resident
              ? "Consulte as autorizações e os horários de entrada e saída registrados para seu apartamento. Esta tela não autoriza novas visitas."
              : "Consulte as autorizações registradas por apartamento e data."}
      </PageHeading>
      <div className="stack">
        <Feedback message={notice} variant="success" />
        {resident && !reservation && (
          <div className="actions">
            <LinkButton route="/assistente" secondary>
              Autorizar visita pelo Assistente
            </LinkButton>
          </div>
        )}
        {details && (
          <ReservationDetails item={details} close={() => setDetails(null)} />
        )}
        {editing && (
          <HoursEditor
            key={editing.id}
            title={"Horários da visita de " + editing.name}
            row={editing}
            fields={visitHours}
            allowOpenEnd
            onSave={updateHours}
            onCancel={() => setEditing(null)}
          />
        )}
        <QueryResult query={query}>
          {(data) => {
            const items = Array.isArray(data) ? data : [];
            const options = new Map(
              items
                .filter((item) => item.area_id)
                .map((item) => [item.area_id, item.area_name ?? item.area_id]),
            );
            const term = search.trim().toLocaleLowerCase("pt-BR");
            const rows = items.filter(
              (item) =>
                (!date || item.date === date) &&
                (!area || item.area_id === area) &&
                (!term ||
                  [item.code, item.name, item.apartment, item.area_name].some(
                    (value) =>
                      String(value ?? "")
                        .toLocaleLowerCase("pt-BR")
                        .includes(term),
                  )),
            );
            return (
              <section className="panel stack" aria-label={title}>
                <div className="filters">
                  <label>
                    <span>
                      {reservation ? "Buscar reserva" : "Buscar visita"}
                    </span>
                    <input
                      type="search"
                      value={search}
                      placeholder={
                        reservation
                          ? "Código ou apartamento"
                          : "Nome ou apartamento"
                      }
                      onChange={(event) => setSearch(event.target.value)}
                    />
                  </label>
                  <label>
                    <span>Data</span>
                    <input
                      type="date"
                      value={date}
                      onChange={(event) => setDate(event.target.value)}
                    />
                  </label>
                  {reservation && (
                    <label>
                      <span>Área</span>
                      <select
                        value={area}
                        onChange={(event) => setArea(event.target.value)}
                      >
                        <option value="">Todas as áreas</option>
                        {[...options].map(([key, name]) => (
                          <option key={key} value={key}>
                            {name}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </div>
                <p className="result-count" aria-live="polite">
                  {rows.length} {rows.length === 1 ? "registro" : "registros"}
                </p>
                <Table
                  label={title}
                  columns={editableColumns}
                  rows={rows}
                  getKey={(item) => item.code ?? item.id}
                  onRowClick={openDetails ? setDetails : undefined}
                />
              </section>
            );
          }}
        </QueryResult>
      </div>
    </>
  );
}

function emphasized(line) {
  return line
    .split("**")
    .map((part, index) =>
      index % 2 ? <strong key={index}>{part}</strong> : part,
    );
}

export function RegulationCopy({ version }) {
  if (!version)
    return (
      <Feedback message="O regulamento está indisponível." variant="warning" />
    );
  return (
    <article className="regulation-copy">
      {String(version.content ?? "")
        .split("\n")
        .map((line, index) => {
          const heading = line.match(/^#{1,6}\s+(.+)$/);
          return heading ? (
            <h3 key={index}>{heading[1]}</h3>
          ) : line.trim() ? (
            <p key={index}>{emphasized(line)}</p>
          ) : (
            <span className="paragraph-break" key={index} aria-hidden="true" />
          );
        })}
    </article>
  );
}
