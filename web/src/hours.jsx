import { useState } from "react";
import { Button, Feedback } from "./ui";

export const reservationHours = [
  { key: "start_time", label: "Início" },
  { key: "end_time", label: "Fim" },
];

export const visitHours = [
  { key: "entry_time", label: "Entrada" },
  { key: "exit_time", label: "Saída" },
];

export function hourValue(value) {
  return /^(?:[01]\d|2[0-3]):[0-5]\d(?::|$)/.test(value ?? "") ? value.slice(0, 5) : "";
}

export function hourLabel(value) {
  return hourValue(value) || "Não informado";
}

export function HoursEditor({ title, row, fields, onSave, onCancel, allowOpenEnd = false }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(fields.map(({ key }) => [key, form.get(key) || null]));
    const start = payload[fields[0].key];
    const end = payload[fields[1].key];
    if (!allowOpenEnd && Boolean(start) !== Boolean(end)) {
      setError("Informe início e fim ou deixe os dois campos em branco.");
      return;
    }
    if (allowOpenEnd && end && !start) {
      setError("Informe a entrada para registrar a saída da visita.");
      return;
    }
    if (start && end && start >= end) {
      setError(allowOpenEnd ? "A saída deve ser posterior à entrada." : "O fim deve ser posterior ao início.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await onSave(payload);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  return <form className="panel editor stack" aria-label={title} onSubmit={submit}>
    <h3>{title}</h3>
    <Feedback message={error} />
    <fieldset className="form-grid" disabled={busy}>
      {fields.map(({ key, label }) => <label key={key}>
        {label}
        <input type="time" name={key} defaultValue={hourValue(row[key])} step="60" />
      </label>)}
    </fieldset>
    <p className="muted">{allowOpenEnd
      ? "Registre a entrada e informe a saída quando ocorrer. Deixe ambos em branco para limpar."
      : "Preencha início e fim. Deixe ambos em branco para limpar."}</p>
    <div className="actions">
      <Button type="submit" disabled={busy}>{busy ? "Salvando…" : "Salvar horários"}</Button>
      <Button variant="secondary" onClick={onCancel} disabled={busy}>Cancelar</Button>
    </div>
  </form>;
}
