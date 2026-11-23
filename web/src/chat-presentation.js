// Adapt the stored, server-authored reservation snapshot for the chat UI.
// Do not interpret user messages as data or fetch the current agenda: an old
// message describes the reservations that were active when it was sent.
const noise = /^Nenhuma alteração foi registrada neste turno\.\r?\n+(?=\S)/;
const snapshot = /^(?:Reservas ativas da sua unidade:)[ \t]*\r?\n(\[(?:\r?\n[\s\S]*?\r?\n\])?)(?=\r?\n\r?\n|$)/m;
const isDay = value => typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);
const isTime = value => typeof value === "string" && /^\d{2}:\d{2}$/.test(value);

export function presentChatMessage(content, role) {
  if (role !== "assistant" || typeof content !== "string") return { text: content };
  const text = content.replace(noise, "");
  const found = snapshot.exec(text);
  if (!found) return { text };
  let rows;
  try { rows = JSON.parse(found[1]); } catch { return { text }; }
  if (!Array.isArray(rows) || !rows.length || !rows.every(row =>
    row && typeof row.area_name === "string" && row.area_name.trim() && isDay(row.date))) return { text };

  return {
    before: text.slice(0, found.index).trim(),
    after: text.slice(found.index + found[0].length).trim(),
    reservations: rows.map(row => {
      const [year, month, day] = row.date.split("-");
      return {
        area: row.area_name,
        date: day + "/" + month + "/" + year,
        time: isTime(row.start_time) && isTime(row.end_time) ? row.start_time + " às " + row.end_time : null,
        fee: Number.isSafeInteger(row.fee_cents) && row.fee_cents >= 0 ? row.fee_cents : null,
        code: typeof row.code === "string" && row.code.trim() ? row.code : null,
      };
    }),
  };
}
