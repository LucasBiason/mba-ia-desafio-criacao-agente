import auroraLogo from "./assets/aurora-logo.svg?no-inline";
import { Button } from "./synapse/Button";
import { Alert } from "./synapse/Alert";

export { Button, Alert };

export const roles = { superuser: "Superusuário", admin: "Administrador", resident: "Morador" };
export const money = cents => new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format((cents ?? 0) / 100);
export const shortDate = date => /^\d{4}-\d{2}-\d{2}$/.test(date ?? "") ? date.split("-").reverse().join("/") : "—";
export const timeLabel = date => {
  if (!date || Number.isNaN(Date.parse(date))) return "—";
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(date));
};

export function Brand({ light = false, onNavigate }) {
  return <a className={"brand" + (light ? " brand-light" : "")} href="#/inicio" aria-label="Residencial Aurora, início" onClick={onNavigate}>
    <img className="brand-mark" src={auroraLogo} alt="" width="128" height="128" />
    <span><strong>Aurora</strong><small>Residencial</small></span>
  </a>;
}

export function PageHeading({ section, title, children, actions }) {
  return <header className="page-heading">
    <div>
      {section && <p className="overline">{section}</p>}
      <h1>{title}</h1>
      {children && <p className="page-description">{children}</p>}
    </div>
    {actions && <div className="actions">{actions}</div>}
  </header>;
}

export function Feedback({ message, variant = "danger" }) {
  return message ? <Alert variant={variant} role={variant === "danger" ? "alert" : "status"}>{message}</Alert> : null;
}

export function QueryResult({ query, children }) {
  if (query.error) return <div className="stack">
    <Feedback message={query.error.message} />
    <div><Button variant="secondary" onClick={query.refresh}>Tentar novamente</Button></div>
  </div>;
  if (query.loading && query.data === undefined) return <p className="load-message" role="status">Carregando…</p>;
  if (query.data === undefined) return null;
  return children(query.data);
}

export function Empty({ title = "Nenhum registro encontrado.", children }) {
  return <div className="empty">
    <strong>{title}</strong>
    {children && <p>{children}</p>}
  </div>;
}

export function Table({ label, columns, rows, getKey }) {
  if (!rows.length) return <Empty />;
  return <div className="table-scroll" tabIndex={0} role="region" aria-label={label}>
    <table>
      <caption className="sr-only">{label}</caption>
      <thead><tr>{columns.map(column => <th scope="col" key={column.title}>{column.title}</th>)}</tr></thead>
      <tbody>{rows.map(row => <tr key={getKey(row)}>{columns.map(column =>
        <td key={column.title}>{column.render(row)}</td>
      )}</tr>)}</tbody>
    </table>
  </div>;
}

export function Field({ label, hint, id, children }) {
  return <div className="field">
    <label htmlFor={id}>{label}</label>
    {children}
    {hint && <small id={id + "-hint"}>{hint}</small>}
  </div>;
}

export function Tag({ children, tone = "neutral" }) {
  return <span className={"tag tag-" + tone}>{children}</span>;
}

export function LinkButton({ route, children, secondary = false }) {
  return <a className={"link-button" + (secondary ? " link-secondary" : "")} href={"#" + route}>{children}</a>;
}
