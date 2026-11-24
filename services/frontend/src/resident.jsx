import { useEffect, useRef, useState } from "react";
import auroraLogo from "./assets/aurora-logo.svg?no-inline";
import "./styles/chat.css";
import {
  chatResponse,
  createDecisionGuard,
  submitConfirmation,
  restoredChatHistory,
} from "./chat-confirmations";
import { scoped, useQuery } from "./api";
import { presentChatMessage } from "./chat-presentation.js";
import {
  Button,
  Empty,
  LinkButton,
  PageHeading,
  QueryResult,
  Tag,
  money,
  timeLabel,
} from "./ui";
import { Records, RegulationCopy } from "./records";

function ResidentHome({ api, apartment, user }) {
  const reservations = useQuery(
    api,
    scoped("/api/resident/reservations", apartment),
  );
  const visits = useQuery(api, scoped("/api/resident/visits", apartment));

  return (
    <>
      <PageHeading
        title="Visão geral"
        section={apartment ? "Apartamento " + apartment : "Área do morador"}
      >
        Acompanhe suas reservas e autorizações de visita.
      </PageHeading>
      <section className="welcome">
        <div>
          <h2>Olá, {user.name?.split(" ")[0]}</h2>
        </div>
        <LinkButton route="/areas" secondary>
          Explorar áreas comuns
        </LinkButton>
      </section>
      {apartment ? (
        <div className="summary-grid" aria-label="Resumo do apartamento">
          <section className="panel metric">
            <h2>Reservas ativas</h2>
            <QueryResult query={reservations}>
              {(items) => (
                <strong className="metric-count">
                  {items.filter((item) => item.status === "active").length}
                </strong>
              )}
            </QueryResult>
            <LinkButton route="/reservas" secondary>
              Abrir minhas reservas
            </LinkButton>
          </section>
          <section className="panel metric">
            <h2>Autorizações de visita</h2>
            <QueryResult query={visits}>
              {(items) => (
                <strong className="metric-count">{items.length}</strong>
              )}
            </QueryResult>
            <LinkButton route="/visitas" secondary>
              Abrir visitas
            </LinkButton>
          </section>
        </div>
      ) : (
        <Empty title="Nenhum apartamento vinculado">
          Peça à administração para associar a sua conta a uma unidade.
        </Empty>
      )}
    </>
  );
}

function ResidentAreas({ api, apartment }) {
  const query = useQuery(api, "/api/areas");
  return (
    <>
      <PageHeading title="Áreas comuns" section="Residencial">
        Confira os espaços cadastrados e a taxa de reserva de cada um.
      </PageHeading>
      <QueryResult query={query}>
        {(items) =>
          items.length ? (
            <div className="summary-grid">
              {items.map((area) => (
                <article className="panel area-card" key={area.id}>
                  <span className="area-mark" aria-hidden="true">
                    <span />
                  </span>
                  <h2>{area.name}</h2>
                  <Tag tone={area.fee_cents ? "neutral" : "positive"}>
                    {area.fee_cents ? money(area.fee_cents) : "Gratuita"}
                  </Tag>
                  {apartment && (
                    <LinkButton route="/assistente" secondary>
                      Consultar pelo assistente
                    </LinkButton>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <Empty />
          )
        }
      </QueryResult>
    </>
  );
}

function ResidentRecords({ api, apartment, kind }) {
  const query = useQuery(api, scoped("/api/resident/" + kind, apartment));
  if (!apartment)
    return (
      <>
        <PageHeading
          title={
            kind === "reservations" ? "Minhas reservas" : "Histórico de visitas"
          }
          section="Área do morador"
        />
        <Empty title="Nenhum apartamento vinculado">
          As consultas ficam disponíveis para as suas unidades cadastradas.
        </Empty>
      </>
    );
  return (
    <Records key={kind + "/" + apartment} kind={kind} query={query} resident />
  );
}

function ResidentRegulation({ api }) {
  const query = useQuery(api, "/api/resident/regulation");
  return (
    <>
      <PageHeading title="Regulamento" section="Residencial">
        Leia as regras em vigor no Aurora.
      </PageHeading>
      <QueryResult query={query}>
        {(version) => (
          <section className="panel regulation-panel">
            <header className="section-heading">
              <h2>Versão vigente</h2>
              <Tag>Versão {version.version}</Tag>
            </header>
            <RegulationCopy version={version} />
          </section>
        )}
      </QueryResult>
    </>
  );
}

function ChatMessageBody({ item }) {
  const reply = presentChatMessage(item.content, item.role);
  if (!reply.reservations) return <p>{reply.text}</p>;
  return (
    <>
      {reply.before && <p>{reply.before}</p>}
      <section
        className="aurora-chat-reservations"
        aria-label="Reservas ativas da sua unidade"
      >
        <h3>
          Suas reservas ativas <span>{reply.reservations.length}</span>
        </h3>
        <ul>
          {reply.reservations.map((reservation, index) => (
            <li key={reservation.code || index}>
              <div className="aurora-chat-reservation-title">
                <strong>{reservation.area}</strong>
                {reservation.fee !== null && (
                  <Tag tone={reservation.fee ? "neutral" : "positive"}>
                    {reservation.fee ? money(reservation.fee) : "Gratuita"}
                  </Tag>
                )}
              </div>
              <div className="aurora-chat-reservation-date">
                {reservation.date}
                {reservation.time && " · " + reservation.time}
              </div>
              {reservation.code && (
                <div className="aurora-chat-reservation-code">
                  Código: {reservation.code}
                </div>
              )}
            </li>
          ))}
        </ul>
      </section>
      {reply.after && <p>{reply.after}</p>}
    </>
  );
}

function Chat({ api, apartment }) {
  const [session, setSession] = useState(null);
  const [historyReady, setHistoryReady] = useState(false);
  const [loadRevision, setLoadRevision] = useState(0);
  const [messages, setMessages] = useState([]);
  const [pending, setPending] = useState([]);
  const [actionsEnabled, setActionsEnabled] = useState(false);
  const [cursor, setCursor] = useState(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState("loading");
  const [notice, setNotice] = useState(null);
  const [decisions, setDecisions] = useState({});
  const guard = useRef(createDecisionGuard());
  const inFlight = useRef(false);
  const timeline = useRef(null);
  const input = useRef(null);
  const atBottom = useRef(true);
  const alive = useRef(true);
  const base =
    session && "/api/resident/chat/sessions/" + encodeURIComponent(session.id);

  function installHistory(data, older = false) {
    const history = restoredChatHistory(data);
    const rows = history.messages;
    setMessages((previous) => {
      const combined = older ? [...rows, ...previous] : rows;
      const seen = new Set();
      return combined.filter(
        (item) => !item.id || (!seen.has(item.id) && seen.add(item.id)),
      );
    });
    setPending(history.pending);
    setActionsEnabled(data.actions_enabled !== false);
    setCursor(history.cursor);
    setHistoryReady(true);
  }

  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    if (!apartment) {
      setBusy("");
      return () => {
        alive.current = false;
      };
    }
    (async () => {
      try {
        const current = await api("/api/resident/chat/sessions", {
          method: "POST",
          body: { apartment },
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setSession(current);
        const history = await api(
          "/api/resident/chat/sessions/" +
            encodeURIComponent(current.id) +
            "/history?limit=50&include_archived=true",
          { signal: controller.signal },
        );
        if (controller.signal.aborted) return;
        installHistory(history);
      } catch (failure) {
        if (!controller.signal.aborted)
          setNotice({ error: true, text: failure.message, refresh: true });
      } finally {
        if (!controller.signal.aborted) setBusy("");
      }
    })();
    return () => {
      alive.current = false;
      controller.abort();
    };
  }, [api, apartment, loadRevision]);

  useEffect(() => {
    if (atBottom.current && timeline.current)
      timeline.current.scrollTop = timeline.current.scrollHeight;
  }, [messages, pending, busy, notice]);

  useEffect(() => {
    const field = input.current;
    if (!field) return;
    field.style.height = "auto";
    field.style.height = Math.min(field.scrollHeight, 160) + "px";
    field.style.overflowY = field.scrollHeight > 160 ? "auto" : "hidden";
  }, [draft]);

  async function reload(older = false) {
    if (inFlight.current) return;
    if (!base) {
      setNotice(null);
      setBusy("loading");
      setLoadRevision((value) => value + 1);
      return;
    }
    inFlight.current = true;
    setBusy(older ? "older" : "refresh");
    const element = timeline.current;
    const height = element?.scrollHeight ?? 0;
    const top = element?.scrollTop ?? 0;
    try {
      const data = await api(
        base +
          "/history?limit=50&include_archived=true" +
          (older && cursor ? "&before=" + encodeURIComponent(cursor) : ""),
      );
      if (!alive.current) return;
      if (older) atBottom.current = false;
      installHistory(data, older);
      if (older)
        requestAnimationFrame(() => {
          if (timeline.current)
            timeline.current.scrollTop =
              top + timeline.current.scrollHeight - height;
        });
      setNotice(null);
    } catch (failure) {
      if (alive.current) setHistoryReady(false);
      if (alive.current)
        setNotice({ error: true, text: failure.message, refresh: true });
    } finally {
      inFlight.current = false;
      if (alive.current) setBusy("");
    }
  }

  async function refreshAfterAction() {
    try {
      const data = await api(base + "/history?limit=50&include_archived=true");
      if (alive.current) installHistory(data);
    } catch {
      if (alive.current) setHistoryReady(false);
      if (alive.current)
        setNotice({
          error: true,
          text: "O serviço respondeu, mas não foi possível atualizar o histórico. Atualize a conversa antes de repetir qualquer ação.",
          refresh: true,
        });
    }
  }

  async function send(event) {
    event.preventDefault();
    if (
      !base ||
      !historyReady ||
      inFlight.current ||
      busy ||
      pending.length ||
      !draft.trim()
    )
      return;
    inFlight.current = true;
    setBusy("send");
    setNotice(null);
    atBottom.current = true;
    const sent = draft.trim();
    setDraft("");
    setMessages((previous) => [
      ...previous,
      { id: "local-" + Date.now(), role: "user", content: sent },
    ]);
    try {
      const result = chatResponse(
        await api(base + "/messages", {
          method: "POST",
          body: { message: sent },
        }),
      );
      if (!alive.current) return;
      if (result.message)
        setMessages((previous) => [
          ...previous,
          { role: "assistant", content: result.message },
        ]);
      if (result.pending !== undefined) setPending(result.pending);
      await refreshAfterAction();
    } catch (failure) {
      if (failure.code === "AGENT_NOT_CONFIGURED") {
        await refreshAfterAction();
        if (alive.current)
          setNotice({
            error: true,
            text: "O assistente está indisponível no momento. Sua conversa foi preservada; tente novamente mais tarde.",
          });
      } else {
        if (alive.current) setHistoryReady(false);
        if (alive.current)
          setNotice({
            error: true,
            text: failure.message + " Confira o histórico antes de reenviar.",
            refresh: true,
          });
      }
    } finally {
      inFlight.current = false;
      if (alive.current) setBusy("");
    }
  }

  async function decide(id, confirmado, sourceSessionId) {
    if (
      !session ||
      !historyReady ||
      !actionsEnabled ||
      inFlight.current ||
      busy ||
      decisions[id]
    )
      return;
    inFlight.current = true;
    setBusy("decision");
    setNotice(null);
    atBottom.current = true;
    setDecisions((previous) => ({ ...previous, [id]: "sending" }));
    try {
      const result = await submitConfirmation(
        api,
        guard.current,
        sourceSessionId || session.id,
        id,
        confirmado,
      );
      if (!alive.current || !result) return;
      if (result.message)
        setMessages((previous) => [
          ...previous,
          { role: "assistant", content: result.message },
        ]);
      setPending(result.pending ?? []);
      setDecisions((previous) => ({ ...previous, [id]: "done" }));
      await refreshAfterAction();
    } catch (failure) {
      if (alive.current) setHistoryReady(false);
      if (alive.current) {
        setDecisions((previous) => ({ ...previous, [id]: "failed" }));
        setNotice({
          error: true,
          text:
            failure.message +
            " Não repita a decisão: confira o histórico e as reservas/visitas.",
          refresh: true,
        });
      }
    } finally {
      inFlight.current = false;
      if (alive.current) setBusy("");
    }
  }

  function composeKeyDown(event) {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  function scrollConversation(event) {
    const element = event.currentTarget;
    atBottom.current =
      element.scrollHeight - element.scrollTop - element.clientHeight < 80;
    if (element.scrollTop < 60 && cursor && !busy && !inFlight.current)
      void reload(true);
  }

  const show = (value) =>
    typeof value === "string" || typeof value === "number"
      ? String(value)
      : "Não informado";
  return (
    <section className="aurora-chat" aria-labelledby="aurora-chat-title">
      <header className="aurora-chat-header">
        <img src={auroraLogo} alt="" width="34" height="34" />
        <div>
          <h1 id="aurora-chat-title">Assistente Aurora</h1>
          <p>
            {apartment
              ? "Sua conversa do apartamento " + apartment
              : "Área do morador"}
          </p>
        </div>
        <span className="aurora-chat-private">Conversa privada</span>
      </header>
      {!apartment ? (
        <Empty title="Nenhum apartamento vinculado">
          Peça à administração para vincular sua unidade.
        </Empty>
      ) : (
        <>
          <div
            className="aurora-chat-timeline"
            ref={timeline}
            role="log"
            aria-label="Histórico da conversa"
            aria-live="polite"
            aria-relevant="additions text"
            onScroll={scrollConversation}
          >
            <div className="aurora-chat-thread">
              {cursor && (
                <div className="aurora-chat-previous">
                  <Button
                    variant="secondary"
                    size="small"
                    disabled={Boolean(busy)}
                    onClick={() => reload(true)}
                  >
                    {busy === "older"
                      ? "Carregando mensagens…"
                      : "Ver mensagens anteriores"}
                  </Button>
                </div>
              )}
              {!messages.length && !busy && !pending.length && !notice && (
                <div className="aurora-chat-empty">
                  <img src={auroraLogo} alt="" width="62" height="62" />
                  <h2>Como posso ajudar?</h2>
                  <p>
                    Cuide das suas reservas, receba suas visitas e consulte as
                    regras do Aurora.
                  </p>
                  <div
                    className="aurora-chat-suggestions"
                    aria-label="Sugestões de mensagem"
                  >
                    {[
                      "Quais são as minhas reservas?",
                      "Qual é o horário da piscina?",
                      "Quero autorizar uma visita",
                    ].map((text) => (
                      <button
                        key={text}
                        type="button"
                        onClick={() => {
                          setDraft(text);
                          input.current?.focus();
                        }}
                      >
                        {text}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((item, index) => (
                <article
                  className={
                    "aurora-chat-message" +
                    (item.role === "user" ? " aurora-chat-mine" : "")
                  }
                  data-message-id={item.id}
                  key={item.id ?? "reply-" + index}
                >
                  <header className="aurora-chat-message-meta">
                    {item.role !== "user" && (
                      <img src={auroraLogo} alt="" width="24" height="24" />
                    )}
                    <strong>{item.role === "user" ? "Você" : "Aurora"}</strong>
                    {item.created_at && (
                      <time dateTime={item.created_at}>
                        {timeLabel(item.created_at)}
                      </time>
                    )}
                  </header>
                  <div className="aurora-chat-message-content">
                    <ChatMessageBody item={item} />
                  </div>
                </article>
              ))}
              {pending.map((item) => (
                <section
                  className="aurora-chat-confirmation"
                  key={item.id}
                  aria-label="Confirmação pendente"
                >
                  <h3>
                    {item.acao === "autorizar_visitante"
                      ? "Autorizar visitante"
                      : "Confirmar reserva"}
                  </h3>
                  <p>Revise os dados. A ação só acontece após sua aprovação.</p>
                  <dl>
                    {item.detalhes.area !== undefined && (
                      <>
                        <dt>Área</dt>
                        <dd>{show(item.detalhes.area)}</dd>
                      </>
                    )}
                    {item.detalhes.nome !== undefined && (
                      <>
                        <dt>Visitante</dt>
                        <dd>{show(item.detalhes.nome)}</dd>
                      </>
                    )}
                    <dt>Data</dt>
                    <dd>{show(item.detalhes.data)}</dd>
                    {item.detalhes.taxa !== undefined && (
                      <>
                        <dt>Taxa</dt>
                        <dd>
                          {typeof item.detalhes.taxa === "number"
                            ? money(item.detalhes.taxa * 100)
                            : show(item.detalhes.taxa)}
                        </dd>
                      </>
                    )}
                    {item.detalhes.hora_inicio && (
                      <>
                        <dt>Início</dt>
                        <dd>{show(item.detalhes.hora_inicio)}</dd>
                      </>
                    )}
                    {item.detalhes.hora_fim && (
                      <>
                        <dt>Fim</dt>
                        <dd>{show(item.detalhes.hora_fim)}</dd>
                      </>
                    )}
                  </dl>
                  <div className="aurora-chat-tools">
                    <Button
                      disabled={
                        !historyReady ||
                        !actionsEnabled ||
                        Boolean(busy) ||
                        Boolean(decisions[item.id])
                      }
                      onClick={() =>
                        decide(
                          item.id,
                          true,
                          item.sourceSessionId || item.session_id,
                        )
                      }
                    >
                      Aprovar
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={
                        !historyReady ||
                        !actionsEnabled ||
                        Boolean(busy) ||
                        Boolean(decisions[item.id])
                      }
                      onClick={() =>
                        decide(
                          item.id,
                          false,
                          item.sourceSessionId || item.session_id,
                        )
                      }
                    >
                      Negar
                    </Button>
                  </div>
                </section>
              ))}
              {(busy || notice) && (
                <div
                  className={
                    "aurora-chat-notice" + (busy ? " aurora-chat-working" : "")
                  }
                  role={notice?.error && !busy ? "alert" : "status"}
                >
                  {busy ? (
                    <>
                      <span className="aurora-chat-dots" aria-hidden="true">
                        <i />
                        <i />
                        <i />
                      </span>
                      <p>
                        {busy === "send"
                          ? "Aurora está respondendo…"
                          : busy === "decision"
                            ? "Processando sua decisão…"
                            : busy === "older"
                              ? "Carregando mensagens anteriores…"
                              : "Carregando sua conversa…"}
                      </p>
                    </>
                  ) : (
                    <>
                      <p>{notice.text}</p>
                      {notice.refresh && (
                        <Button
                          size="small"
                          variant="secondary"
                          onClick={() => reload()}
                        >
                          Tentar novamente
                        </Button>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="aurora-chat-composer-area">
            <form className="aurora-chat-compose" onSubmit={send}>
              <label htmlFor="aurora-chat-message" className="visually-hidden">
                Mensagem
              </label>
              <textarea
                id="aurora-chat-message"
                ref={input}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={composeKeyDown}
                rows={1}
                maxLength={2000}
                aria-describedby="aurora-chat-compose-hint"
                placeholder={
                  pending.length
                    ? "Aprove ou negue o pedido acima para continuar"
                    : "Escreva para o Aurora…"
                }
                disabled={!session}
                required
              />
              <Button
                type="submit"
                aria-label="Enviar"
                disabled={
                  !session ||
                  !historyReady ||
                  Boolean(busy) ||
                  pending.length > 0 ||
                  !draft.trim()
                }
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="m6 12 6-6 6 6M12 6v13" />
                </svg>
              </Button>
            </form>
            <p
              id="aurora-chat-compose-hint"
              className="aurora-chat-compose-hint"
            >
              Enter para enviar · Shift + Enter para uma nova linha
            </p>
          </div>
        </>
      )}
    </section>
  );
}

export function Resident({ api, path, user, apartment }) {
  switch (path) {
    case "/areas":
      return <ResidentAreas api={api} apartment={apartment} />;
    case "/reservas":
      return (
        <ResidentRecords api={api} apartment={apartment} kind="reservations" />
      );
    case "/visitas":
      return <ResidentRecords api={api} apartment={apartment} kind="visits" />;
    case "/regulamento":
      return <ResidentRegulation api={api} />;
    case "/assistente":
      return <Chat key={apartment ?? "none"} api={api} apartment={apartment} />;
    default:
      return <ResidentHome api={api} apartment={apartment} user={user} />;
  }
}
