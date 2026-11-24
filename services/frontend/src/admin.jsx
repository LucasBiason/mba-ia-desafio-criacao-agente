import { useState } from "react";
import { useQuery } from "./api";
import {
  Button,
  Empty,
  Feedback,
  Field,
  LinkButton,
  PageHeading,
  QueryResult,
  Table,
  Tag,
  money,
  roles,
  timeLabel,
} from "./ui";
import { Records, RegulationCopy } from "./records";
import { Agenda } from "./agenda";

function WorkspaceEditor({ config, api }) {
  const rows = useQuery(api, config.collection);
  const [editor, setEditor] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  function open(item) {
    setEditor({ item });
    setDeleting(false);
    setError("");
    setNotice("");
  }

  async function mutate(method, body) {
    setError("");
    setBusy(true);
    try {
      const key = config.routeKey ?? config.key;
      const url = editor.item
        ? config.collection + "/" + encodeURIComponent(key(editor.item))
        : config.collection;
      await api(url, { method, body });
      setEditor(null);
      setDeleting(false);
      setNotice(method === "DELETE" ? "Cadastro excluído." : "Cadastro salvo.");
      rows.refresh();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  function submit(event) {
    event.preventDefault();
    if (busy) return;
    const form = new FormData(event.currentTarget);
    mutate(editor.item ? "PATCH" : "POST", config.payload(form, editor.item));
  }

  function cancel() {
    setEditor(null);
    setDeleting(false);
    setError("");
  }

  return (
    <>
      <PageHeading
        title={config.title}
        section="Administração"
        actions={
          !editor && <Button onClick={() => open(null)}>{config.create}</Button>
        }
      >
        {config.description}
      </PageHeading>
      <div className="stack">
        <Feedback message={notice} variant="success" />
        {editor && (
          <section
            className="panel editor"
            aria-label={editor.item ? "Editar cadastro" : "Novo cadastro"}
          >
            <header className="section-heading">
              <h2>
                {editor.item
                  ? "Editar " + config.label(editor.item)
                  : config.create}
              </h2>
            </header>
            <div className="stack">
              <Feedback message={error} />
              {deleting ? (
                <div className="stack">
                  <p>
                    Excluir <strong>{config.label(editor.item)}</strong>?
                  </p>
                  <div className="actions">
                    <Button
                      variant="danger"
                      disabled={busy}
                      onClick={() => mutate("DELETE")}
                    >
                      Confirmar exclusão
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={busy}
                      onClick={() => {
                        setDeleting(false);
                        setError("");
                      }}
                    >
                      Voltar
                    </Button>
                  </div>
                </div>
              ) : (
                <form
                  className="stack"
                  onSubmit={submit}
                  key={editor.item ? config.key(editor.item) : "new"}
                >
                  <fieldset className="form-grid" disabled={busy}>
                    {config.fields(editor.item)}
                  </fieldset>
                  <div className="actions">
                    <Button type="submit" disabled={busy}>
                      {busy ? "Salvando…" : "Salvar"}
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={busy}
                      onClick={cancel}
                    >
                      Cancelar
                    </Button>
                    {config.canDelete && editor.item && (
                      <Button
                        variant="danger"
                        disabled={busy}
                        onClick={() => {
                          setDeleting(true);
                          setError("");
                        }}
                      >
                        Excluir
                      </Button>
                    )}
                  </div>
                </form>
              )}
            </div>
          </section>
        )}
        <QueryResult query={rows}>
          {(data) => (
            <section className="panel stack">
              <div className="section-heading">
                <h2>Cadastros</h2>
                <p>
                  {data.length} {data.length === 1 ? "registro" : "registros"}
                </p>
              </div>
              <Table
                label={config.title}
                rows={data}
                getKey={config.key}
                columns={[
                  ...config.columns,
                  {
                    title: "Ações",
                    render: (record) => (
                      <Button
                        size="small"
                        variant="secondary"
                        disabled={busy}
                        aria-label={"Editar " + config.label(record)}
                        onClick={() => open(record)}
                      >
                        Editar
                      </Button>
                    ),
                  },
                ]}
              />
            </section>
          )}
        </QueryResult>
      </div>
    </>
  );
}

function Users({ api }) {
  const config = {
    title: "Usuários",
    create: "Novo usuário",
    description:
      "Cadastre moradores e administradores e gerencie o acesso ao portal.",
    collection: "/api/admin/users",
    key: (item) => item.id,
    label: (item) => item.name,
    columns: [
      { title: "Nome", render: (item) => <strong>{item.name}</strong> },
      { title: "E-mail", render: (item) => item.email },
      { title: "Perfil", render: (item) => roles[item.role] ?? item.role },
      {
        title: "Acesso",
        render: (item) => (
          <Tag tone={item.active ? "positive" : "neutral"}>
            {item.active ? "Ativo" : "Inativo"}
          </Tag>
        ),
      },
    ],
    fields(item) {
      return (
        <>
          <label>
            Nome
            <input
              autoComplete="off"
              name="name"
              defaultValue={item?.name ?? ""}
              maxLength={100}
              required
            />
          </label>
          <label>
            E-mail
            <input
              type="email"
              autoComplete="off"
              name="email"
              defaultValue={item?.email ?? ""}
              maxLength={254}
              required
            />
          </label>
          {item ? (
            <label>
              Perfil
              <input readOnly value={roles[item.role] ?? item.role} />
            </label>
          ) : (
            <label>
              Perfil
              <select name="role" aria-label="Perfil" defaultValue="resident">
                <option value="resident">Morador</option>
                <option value="admin">Administrador</option>
              </select>
            </label>
          )}
          {item && (
            <label>
              Acesso
              <select
                name="active"
                aria-label="Acesso"
                defaultValue={String(item.active)}
              >
                <option value="true">Ativo</option>
                <option value="false">Inativo</option>
              </select>
            </label>
          )}
          <Field
            id="user-password"
            label={item ? "Nova senha (opcional)" : "Senha"}
            hint="Mínimo de 12 caracteres."
          >
            <input
              id="user-password"
              aria-describedby="user-password-hint"
              type="password"
              name="password"
              autoComplete="new-password"
              required={!item}
              minLength={12}
              maxLength={256}
            />
          </Field>
        </>
      );
    },
    payload(data, item) {
      const body = {
        name: data.get("name").trim(),
        email: data.get("email").trim(),
      };
      if (data.has("role")) body.role = data.get("role");
      if (item) body.active = data.get("active") === "true";
      if (data.get("password")) body.password = data.get("password");
      return body;
    },
  };
  return <WorkspaceEditor api={api} config={config} />;
}

function Apartments({ api }) {
  const users = useQuery(api, "/api/admin/users");
  return (
    <QueryResult query={users}>
      {(accounts) => {
        const residents = accounts.filter(
          (account) => account.role === "resident",
        );
        const names = new Map(
          residents.map((account) => [account.id, account.name]),
        );
        const config = {
          title: "Apartamentos",
          create: "Novo apartamento",
          description:
            "O morador responsável pela unidade é também o proprietário.",
          collection: "/api/admin/apartments",
          key: (item) => item.id,
          routeKey: (item) => item.number,
          label: (item) => "Apartamento " + item.number,
          canDelete: true,
          columns: [
            { title: "Código", render: (item) => item.id },
            {
              title: "Número",
              render: (item) => <strong>{item.number}</strong>,
            },
            {
              title: "Morador responsável",
              render: (item) =>
                item.resident_id ? (
                  (names.get(item.resident_id) ?? <Tag>Não identificado</Tag>)
                ) : (
                  <Tag>Sem responsável</Tag>
                ),
            },
          ],
          fields: (item) => (
            <>
              <label>
                Número
                <input
                  name="number"
                  defaultValue={item?.number ?? ""}
                  inputMode="numeric"
                  pattern="[0-9]{1,10}[A-Za-z]?"
                  maxLength={11}
                  required
                />
              </label>
              <label>
                Morador responsável
                <select
                  name="resident_id"
                  aria-label="Morador responsável"
                  defaultValue={item?.resident_id ?? ""}
                >
                  <option value="">Sem responsável</option>
                  {residents.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              </label>
            </>
          ),
          payload: (form) => ({
            number: form.get("number").trim(),
            resident_id: form.get("resident_id") || null,
          }),
        };
        return <WorkspaceEditor api={api} config={config} />;
      }}
    </QueryResult>
  );
}

function Areas({ api }) {
  const config = {
    title: "Áreas comuns",
    create: "Nova área",
    description: "Mantenha o catálogo e as taxas exibidas aos moradores.",
    collection: "/api/admin/areas",
    key: (item) => item.id,
    label: (item) => item.name,
    canDelete: true,
    columns: [
      { title: "Nome", render: (item) => <strong>{item.name}</strong> },
      { title: "Identificador", render: (item) => item.id },
      {
        title: "Taxa",
        render: (item) =>
          item.fee_cents ? (
            money(item.fee_cents)
          ) : (
            <Tag tone="positive">Gratuita</Tag>
          ),
      },
    ],
    fields: (item) => (
      <>
        <label>
          Nome
          <input
            name="name"
            defaultValue={item?.name ?? ""}
            maxLength={120}
            required
          />
        </label>
        <Field
          id="area-identifier"
          label="Identificador"
          hint="Exemplo: sala-de-jogos"
        >
          <input
            id="area-identifier"
            aria-describedby="area-identifier-hint"
            name="id"
            defaultValue={item?.id ?? ""}
            readOnly={Boolean(item)}
            required
            pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
            maxLength={64}
          />
        </Field>
        <label>
          Taxa (R$)
          <input
            type="number"
            name="price"
            inputMode="decimal"
            min="0"
            max="1000000"
            step="0.01"
            defaultValue={item ? (item.fee_cents / 100).toFixed(2) : "0"}
            required
          />
        </label>
      </>
    ),
    payload(form, item) {
      const body = {
        name: form.get("name").trim(),
        fee_cents: Math.round(Number(form.get("price")) * 100),
      };
      return item ? body : { ...body, id: form.get("id").trim() };
    },
  };
  return <WorkspaceEditor api={api} config={config} />;
}

function RegulationForm({ item, api, onPublished, refresh }) {
  const [text, setText] = useState(item.content);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function publish(event) {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      await api("/api/admin/regulation", {
        method: "PUT",
        body: { base_version: item.version, content: text },
      });
      onPublished();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="panel stack" onSubmit={publish}>
      <div className="section-heading">
        <h2>Editar versão vigente</h2>
        <Tag>Versão {item.version}</Tag>
      </div>
      <Feedback message={error} />
      <label>
        Conteúdo do regulamento
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={15}
          maxLength={200000}
          required
        />
      </label>
      <div className="actions">
        <Button
          type="submit"
          disabled={saving || !text.trim() || text === item.content}
        >
          {saving ? "Publicando…" : "Publicar nova versão"}
        </Button>
        <Button variant="secondary" disabled={saving} onClick={refresh}>
          Recarregar versão vigente
        </Button>
      </div>
    </form>
  );
}

function Regulation({ api }) {
  const current = useQuery(api, "/api/admin/regulation");
  const history = useQuery(api, "/api/admin/regulation/versions");
  const [notice, setNotice] = useState("");

  return (
    <>
      <PageHeading title="Regulamento" section="Administração">
        Publique alterações e consulte o histórico de versões.
      </PageHeading>
      <div className="stack">
        <Feedback message={notice} variant="success" />
        <QueryResult query={current}>
          {(item) => (
            <RegulationForm
              key={item.version}
              item={item}
              api={api}
              onPublished={() => {
                setNotice("Versão publicada.");
                current.refresh();
                history.refresh();
              }}
              refresh={current.refresh}
            />
          )}
        </QueryResult>
        {current.data && (
          <p className="muted">
            Versão {current.data.version} vigente desde{" "}
            {timeLabel(current.data.published_at)}.
          </p>
        )}
        <section className="panel stack">
          <div className="section-heading">
            <h2>Histórico de versões</h2>
          </div>
          <QueryResult query={history}>
            {(items) =>
              items.length ? (
                items.map((item) => (
                  <details key={item.version}>
                    <summary>
                      Versão {item.version} ·{" "}
                      {item.author_name || "Publicação inicial"} ·{" "}
                      {timeLabel(item.published_at)}
                    </summary>
                    <RegulationCopy version={item} />
                  </details>
                ))
              ) : (
                <Empty />
              )
            }
          </QueryResult>
        </section>
      </div>
    </>
  );
}

function AdminVisits({ api }) {
  const query = useQuery(api, "/api/admin/visits");
  return (
    <Records
      query={query}
      kind="visits"
      saveHours={(id, body) =>
        api("/api/admin/visits/" + encodeURIComponent(id) + "/hours", {
          method: "PATCH",
          body,
        })
      }
    />
  );
}

function AdminHome({ api, user }) {
  const apartments = useQuery(api, "/api/admin/apartments");
  const areas = useQuery(api, "/api/admin/areas");
  const reservations = useQuery(api, "/api/admin/reservations");
  const cards = [
    ["Apartamentos", apartments, "/admin/apartamentos", "Ver apartamentos"],
    ["Áreas comuns", areas, "/admin/areas", "Ver áreas"],
    ["Reservas", reservations, "/admin/reservas", "Abrir agenda"],
  ];
  return (
    <>
      <PageHeading title="Visão geral" section="Administração">
        Acompanhe os cadastros e a agenda do residencial.
      </PageHeading>
      <section className="welcome">
        <div>
          <h2>Olá, {user.name?.split(" ")[0]}</h2>
        </div>
        <LinkButton route="/admin/usuarios" secondary>
          Gerenciar usuários
        </LinkButton>
      </section>
      <div className="summary-grid" aria-label="Resumo de cadastros">
        {cards.map(([title, data, route, action]) => (
          <section className="panel metric" key={title}>
            <h2>{title}</h2>
            <QueryResult query={data}>
              {(items) => (
                <strong className="metric-count">{items.length}</strong>
              )}
            </QueryResult>
            <LinkButton route={route} secondary>
              {action}
            </LinkButton>
          </section>
        ))}
      </div>
    </>
  );
}

export function Admin({ api, path, user }) {
  switch (path) {
    case "/admin/apartamentos":
      return <Apartments api={api} />;
    case "/admin/usuarios":
      return <Users api={api} />;
    case "/admin/areas":
      return <Areas api={api} />;
    case "/admin/regulamento":
      return <Regulation api={api} />;
    case "/admin/reservas":
      return <Agenda api={api} />;
    case "/admin/visitas":
      return <AdminVisits api={api} />;
    default:
      return <AdminHome api={api} user={user} />;
  }
}
