import { useState } from "react";
import { scoped, useQuery } from "./api";
import { Button, Empty, Feedback, LinkButton, PageHeading, QueryResult, Tag, money, timeLabel } from "./ui";
import { Records, RegulationCopy } from "./records";

function ResidentHome({ api, apartment, user }) {
  const reservations = useQuery(api, scoped("/api/resident/reservations", apartment));
  const visits = useQuery(api, scoped("/api/resident/visits", apartment));

  return <>
    <PageHeading title="Visão geral" section={apartment ? "Apartamento " + apartment : "Área do morador"}>
      Acompanhe suas reservas e autorizações de visita.
    </PageHeading>
    <section className="welcome">
      <div><h2>Olá, {user.name?.split(" ")[0]}</h2></div>
      <LinkButton route="/areas" secondary>Explorar áreas comuns</LinkButton>
    </section>
    {apartment ? <div className="summary-grid" aria-label="Resumo do apartamento">
      <section className="panel metric">
        <h2>Reservas ativas</h2>
        <QueryResult query={reservations}>{items =>
          <strong className="metric-count">{items.filter(item => item.status === "active").length}</strong>}</QueryResult>
        <LinkButton route="/reservas" secondary>Abrir minhas reservas</LinkButton>
      </section>
      <section className="panel metric">
        <h2>Autorizações de visita</h2>
        <QueryResult query={visits}>{items => <strong className="metric-count">{items.length}</strong>}</QueryResult>
        <LinkButton route="/visitas" secondary>Abrir visitas</LinkButton>
      </section>
    </div> : <Empty title="Nenhum apartamento vinculado">Peça à administração para associar a sua conta a uma unidade.</Empty>}
  </>;
}

function ResidentAreas({ api, apartment }) {
  const query = useQuery(api, "/api/areas");
  return <>
    <PageHeading title="Áreas comuns" section="Residencial">Confira os espaços cadastrados e a taxa de reserva de cada um.</PageHeading>
    <QueryResult query={query}>{items => items.length ? <div className="summary-grid">
      {items.map(area => <article className="panel area-card" key={area.id}>
        <span className="area-mark" aria-hidden="true"><span /></span>
        <h2>{area.name}</h2>
        <Tag tone={area.fee_cents ? "neutral" : "positive"}>{area.fee_cents ? money(area.fee_cents) : "Gratuita"}</Tag>
        {apartment && <LinkButton route="/assistente" secondary>Consultar pelo assistente</LinkButton>}
      </article>)}
    </div> : <Empty />}</QueryResult>
  </>;
}

function ResidentRecords({ api, apartment, kind }) {
  const query = useQuery(api, scoped("/api/resident/" + kind, apartment));
  if (!apartment) return <>
    <PageHeading title={kind === "reservations" ? "Minhas reservas" : "Autorizações de visita"} section="Área do morador" />
    <Empty title="Nenhum apartamento vinculado">As consultas ficam disponíveis para as suas unidades cadastradas.</Empty>
  </>;
  return <Records key={kind + "/" + apartment} kind={kind} query={query} resident />;
}

function ResidentRegulation({ api }) {
  const query = useQuery(api, "/api/resident/regulation");
  return <>
    <PageHeading title="Regulamento" section="Residencial">Leia as regras em vigor no Aurora.</PageHeading>
    <QueryResult query={query}>{version => <section className="panel regulation-panel">
      <header className="section-heading"><h2>Versão vigente</h2><Tag>Versão {version.version}</Tag></header>
      <RegulationCopy version={version} />
    </section>}</QueryResult>
  </>;
}

function Chat({ api, apartment }) {
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState("");
  const [starting, setStarting] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const list = useQuery(api, apartment ? "/api/resident/chat/sessions" : null);
  const sessions = (list.data ?? []).filter(item => item.apartment === apartment);
  const selectedId = selected ?? sessions[0]?.id;
  const sessionPath = selectedId && "/api/resident/chat/sessions/" + encodeURIComponent(selectedId);
  const current = useQuery(api, sessionPath);

  async function start() {
    setError(null);
    setStarting(true);
    try {
      const session = await api("/api/resident/chat/sessions", { method: "POST", body: { apartment } });
      setSelected(session.id);
      setMessage("");
      list.refresh();
    } catch (failure) {
      setError(failure);
    } finally {
      setStarting(false);
    }
  }

  async function send(event) {
    event.preventDefault();
    if (sending || !message.trim()) return;
    setError(null);
    setSending(true);
    try {
      await api(sessionPath + "/messages", { method: "POST", body: { message: message.trim() } });
      setMessage("");
      current.refresh();
    } catch (failure) {
      setError(failure);
    } finally {
      setSending(false);
    }
  }

  return <>
    <PageHeading title="Assistente" section={apartment ? "Apartamento " + apartment : "Área do morador"}
      actions={apartment && <Button disabled={starting} onClick={start}>{starting ? "Abrindo…" : "Nova conversa"}</Button>}>
      Consulte a disponibilidade de áreas, reservas e regras do residencial.
    </PageHeading>
    {!apartment ? <Empty title="Nenhum apartamento vinculado">O assistente abre uma sessão na unidade selecionada.</Empty> : <div className="stack">
      <Feedback variant="warning" message="As conversas ficam vinculadas ao seu apartamento. O serviço de agentes ainda está aguardando configuração." />
      <Feedback message={error?.message} variant={error?.code === "AGENT_NOT_CONFIGURED" ? "warning" : "danger"} />
      <QueryResult query={list}>{() => <div className="chat-layout">
        <section className="panel conversations">
          <h2>Conversas</h2>
          {sessions.length ? sessions.map(session => <button type="button" className="conversation" key={session.id}
            aria-pressed={session.id === selectedId} onClick={() => { setSelected(session.id); setError(null); setMessage(""); }}>
            <strong>Unidade {session.apartment}</strong><small>{timeLabel(session.created_at)}</small>
          </button>) : <p className="muted">Abra uma conversa para começar.</p>}
        </section>
        <section className="panel chat-conversation" aria-label="Conversa">
          {selectedId ? <QueryResult query={current}>{session => <>
            <header className="section-heading"><h2>Conversa do apartamento {session.apartment}</h2></header>
            <div className="chat-history" aria-label="Histórico da conversa">
              {session.messages?.length ? session.messages.map((item, index) =>
                <div className={"chat-message" + (item.role === "user" ? " chat-self" : "")} key={item.id ?? index}>
                  <strong>{item.role === "user" ? "Você" : "Assistente"}</strong><p>{item.content ?? item.message}</p>
                </div>)
                : <Empty title="A conversa ainda está vazia." />}
            </div>
            <form className="chat-compose" onSubmit={send}>
              <label>Mensagem<textarea value={message} onChange={event => setMessage(event.target.value)}
                rows={3} placeholder="Escreva sua pergunta" maxLength={2000} required /></label>
              <Button type="submit" disabled={sending || !message.trim()}>{sending ? "Enviando…" : "Enviar"}</Button>
            </form>
          </>}</QueryResult> : <Empty title="Selecione ou inicie uma conversa." />}
        </section>
      </div>}</QueryResult>
    </div>}
  </>;
}

export function Resident({ api, path, user, apartment }) {
  switch (path) {
    case "/areas": return <ResidentAreas api={api} apartment={apartment} />;
    case "/reservas": return <ResidentRecords api={api} apartment={apartment} kind="reservations" />;
    case "/visitas": return <ResidentRecords api={api} apartment={apartment} kind="visits" />;
    case "/regulamento": return <ResidentRegulation api={api} />;
    case "/assistente": return <Chat key={apartment ?? "none"} api={api} apartment={apartment} />;
    default: return <ResidentHome api={api} apartment={apartment} user={user} />;
  }
}
