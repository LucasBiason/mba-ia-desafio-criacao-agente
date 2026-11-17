import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { request, useQuery } from "./api";
import { Admin } from "./admin";
import { Resident } from "./resident";
import { Brand, Button, Feedback, PageHeading, roles } from "./ui";

const tokenKey = "aurora.session";
const adminNavigation = [
  ["/inicio", "Visão geral", "home"],
  ["/admin/apartamentos", "Apartamentos", "building"],
  ["/admin/usuarios", "Usuários", "users"],
  ["/admin/areas", "Áreas comuns", "areas"],
  ["/admin/reservas", "Agenda", "calendar"],
  ["/admin/visitas", "Visitas", "visits"],
  ["/admin/regulamento", "Regulamento", "book"],
];
const residentNavigation = [
  ["/inicio", "Visão geral", "home"],
  ["/areas", "Áreas comuns", "areas"],
  ["/reservas", "Minhas reservas", "calendar"],
  ["/visitas", "Visitas", "visits"],
  ["/regulamento", "Regulamento", "book"],
  ["/assistente", "Assistente", "chat"],
];

const iconPaths = {
  home: "M3 10 12 3l9 7v10H3z M9 20v-6h6v6",
  building: "M5 21V3h14v18 M3 21h18 M9 7h.01 M15 7h.01 M9 11h.01 M15 11h.01 M10 21v-5h4v5",
  users: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M22 21v-2a4 4 0 0 0-3-4 M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M17 3a4 4 0 0 1 0 8",
  areas: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  calendar: "M3 5h18v16H3z M7 3v4 M17 3v4 M3 10h18 M8 15h.01 M12 15h.01 M16 15h.01",
  visits: "M11 5H4v14h7 M10 12h11 M17 8l4 4-4 4",
  book: "M5 3h14v18H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2 M3 17h16 M8 7h7 M8 11h5",
  chat: "M21 11a8 8 0 0 1-8 8H4l1.5-4A8 8 0 1 1 21 11Z M8 11h.01 M12 11h.01 M16 11h.01",
  menu: "M4 6h16 M4 12h16 M4 18h16",
  close: "m6 6 12 12 M18 6 6 18",
  collapse: "m14 6-6 6 6 6",
  expand: "m10 6 6 6-6 6",
};

function NavigationIcon({ name }) {
  return <svg className="navigation-icon" width="20" height="20" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"
    strokeLinejoin="round" aria-hidden="true" focusable="false">
    <path d={iconPaths[name]} />
  </svg>;
}

function PortalNavigation({ id, navigation, path, section, compact = false, onNavigate }) {
  return <nav id={id} aria-label={section}>
    <p className="overline">{section}</p>
    {navigation.map(([to, label, icon]) => <a key={to} href={"#" + to}
      aria-current={path === to ? "page" : undefined} aria-label={label}
      title={compact ? label : undefined} onClick={onNavigate}>
      <NavigationIcon name={icon} />
      <span className="navigation-label">{label}</span>
    </a>)}
  </nav>;
}

function onRouteChange(callback) {
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
}

function Login({ onLogin, restoring, error, retry }) {
  const [form, setForm] = useState({ email: "", password: "" });
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  async function signIn(event) {
    event.preventDefault();
    setNotice("");
    setBusy(true);
    try {
      const session = await request("/api/auth/login", { method: "POST", body: form });
      onLogin(session);
    } catch (failure) {
      setNotice(failure.message);
    } finally {
      setBusy(false);
    }
  }

  return <main className="login">
    <section className="login-hero">
      <Brand light />
      <div className="login-copy">
        <p className="overline">Portal do residencial</p>
        <h1>Bem-vindo<br />ao Aurora.</h1>
        <p>Áreas comuns, agenda e vida no condomínio em um só lugar.</p>
      </div>
      <div className="login-decoration" aria-hidden="true" />
    </section>
    <section className="login-panel" aria-label="Acesso ao portal">
      <div className="login-content">
        <h2>Entrar</h2>
        <p className="muted">Use a conta cadastrada pela administração.</p>
        {restoring
          ? <p className="load-message" role="status">Verificando sua sessão…</p>
          : <form className="stack login-form" onSubmit={signIn}>
            <Feedback message={notice || error} />
            {error && <div><Button variant="secondary" onClick={retry}>Verificar sessão</Button></div>}
            <label>E-mail
              <input value={form.email} type="email" autoComplete="username" inputMode="email" placeholder="nome@exemplo.com"
                onChange={event => setForm({ ...form, email: event.target.value })} required maxLength={254} />
            </label>
            <label htmlFor="password-input">Senha</label>
            <div className="password-field">
              <input id="password-input" value={form.password} type={show ? "text" : "password"} autoComplete="current-password"
                onChange={event => setForm({ ...form, password: event.target.value })} required maxLength={256} />
              <button type="button" className="text-button" onClick={() => setShow(value => !value)} aria-controls="password-input" aria-pressed={show}>
                {show ? "Ocultar" : "Mostrar"}
              </button>
            </div>
            <Button size="large" type="submit" disabled={busy}>{busy ? "Entrando…" : "Entrar no portal"}</Button>
          </form>}
      </div>
    </section>
  </main>;
}

function Profile({ user }) {
  return <>
    <PageHeading title="Meu perfil" section="Conta">Confira os dados da sua conta.</PageHeading>
    <dl className="panel profile-details">
      <div><dt>Nome</dt><dd>{user.name}</dd></div>
      <div><dt>E-mail</dt><dd>{user.email}</dd></div>
      <div><dt>Perfil</dt><dd>{roles[user.role]}</dd></div>
    </dl>
  </>;
}

function Shell({ user, api, logout, logoutBusy, logoutError }) {
  const administrator = user.role === "admin" || user.role === "superuser";
  const navigation = administrator ? adminNavigation : residentNavigation;
  const hash = useSyncExternalStore(onRouteChange, () => window.location.hash);
  const raw = hash.replace(/^#/, "");
  const path = raw === "/perfil" || navigation.some(([candidate]) => candidate === raw) ? raw : "/inicio";
  const [compact, setCompact] = useState(false);
  const drawer = useRef(null);
  const closeMenuButton = useRef(null);
  const content = useRef(null);
  const section = administrator ? "Administração" : "Área do morador";

  useEffect(() => {
    const desktop = window.matchMedia("(min-width: 721px)");
    const closeOnDesktop = event => {
      if (event.matches && drawer.current?.open) {
        drawer.current.close();
        content.current?.focus();
      }
    };
    desktop.addEventListener("change", closeOnDesktop);
    return () => desktop.removeEventListener("change", closeOnDesktop);
  }, []);

  function navigateFromDrawer() {
    drawer.current?.close();
    content.current?.focus();
  }
  const [chosenApartment, setChosenApartment] = useState(null);
  const apartments = useQuery(api, administrator ? null : "/api/resident/apartments");
  const apartmentList = apartments.data ?? [];
  const apartment = apartmentList.some(item => item.number === chosenApartment)
    ? chosenApartment : apartmentList[0]?.number;
  const title = path === "/perfil" ? "Meu perfil" : navigation.find(([to]) => to === path)?.[1];

  useEffect(() => {
    document.title = title + " · Residencial Aurora";
    window.scrollTo(0, 0);
  }, [title]);

  return <div className={compact ? "workspace workspace-compact" : "workspace"}>
    <a className="skip-link" href="#conteudo" onClick={event => { event.preventDefault(); content.current?.focus(); }}>Pular para o conteúdo</a>
    <aside className="sidebar">
      <div className="sidebar-head">
        <Brand />
        <button className="navigation-button" type="button" aria-expanded={!compact} aria-controls="navigation"
          aria-label={compact ? "Expandir menu" : "Recolher menu"}
          title={compact ? "Expandir menu" : "Recolher menu"} onClick={() => setCompact(value => !value)}>
          <NavigationIcon name={compact ? "expand" : "collapse"} />
        </button>
      </div>
      <PortalNavigation id="navigation" navigation={navigation} path={path} section={section} compact={compact} />
    </aside>
    <dialog id="menu-mobile" className="navigation-drawer" aria-labelledby="menu-mobile-title" ref={drawer}
      onClick={event => { if (event.target === event.currentTarget) drawer.current.close(); }}>
      <div className="drawer-inner">
        <div className="sidebar-head">
          <Brand onNavigate={navigateFromDrawer} />
          <button className="navigation-button" type="button" ref={closeMenuButton} aria-label="Fechar menu" onClick={() => drawer.current.close()}>
            <NavigationIcon name="close" />
          </button>
        </div>
        <h2 id="menu-mobile-title" className="visually-hidden">Menu do portal</h2>
        <PortalNavigation navigation={navigation} path={path} section={section} onNavigate={navigateFromDrawer} />
      </div>
    </dialog>
    <div className="main-area">
      <header className="topbar">
        <div className="topbar-context">
          <button className="navigation-button mobile-menu-button" type="button" aria-label="Abrir menu"
            aria-haspopup="dialog" aria-controls="menu-mobile" onClick={() => { drawer.current.showModal(); closeMenuButton.current.focus(); }}>
            <NavigationIcon name="menu" />
          </button>
          {administrator ? <span className="topbar-label">Gestão do residencial</span>
            : <label className="unit-picker">
              <span>Apartamento</span>
              <select aria-label="Apartamento ativo" value={apartment ?? ""} onChange={event => setChosenApartment(event.target.value)}
                disabled={!apartmentList.length}>
                {!apartmentList.length && <option value="">{apartments.loading ? "Carregando…" : "Sem vínculo"}</option>}
                {apartmentList.map(item => <option value={item.number} key={item.number}>{item.number}</option>)}
              </select>
            </label>}
        </div>
        <div className="topbar-account">
          <a href="#/perfil" aria-current={path === "/perfil" ? "page" : undefined} className="account">
            <span className="avatar" aria-hidden="true">{user.name?.trim()?.[0]?.toUpperCase() ?? "A"}</span>
            <span className="account-copy"><strong>{user.name}</strong><small>{roles[user.role]}</small></span>
          </a>
          <Button variant="secondary" size="small" disabled={logoutBusy} onClick={logout}>{logoutBusy ? "Saindo…" : "Sair"}</Button>
        </div>
      </header>
      <main id="conteudo" ref={content} tabIndex={-1} className="content">
        <Feedback message={logoutError} />
        {!administrator && apartments.error && <div className="stack feedback-wrap">
          <Feedback message={apartments.error.message} />
          <div><Button variant="secondary" onClick={apartments.refresh}>Consultar apartamentos novamente</Button></div>
        </div>}
        {path === "/perfil" ? <Profile user={user} />
          : administrator ? <Admin api={api} path={path} user={user} />
          : <Resident api={api} path={path} user={user} apartment={apartment} />}
      </main>
    </div>
  </div>;
}

export function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem(tokenKey));
  const [user, setUser] = useState(null);
  const [bootError, setBootError] = useState("");
  const [revision, setRevision] = useState(0);
  const [logoutBusy, setLogoutBusy] = useState(false);
  const [logoutError, setLogoutError] = useState("");

  const clearSession = useCallback(() => {
    sessionStorage.removeItem(tokenKey);
    setToken(null);
    setUser(null);
    setBootError("");
    setLogoutError("");
    document.title = "Residencial Aurora";
  }, []);

  const api = useCallback(async (path, options = {}) => {
    try {
      return await request(path, { ...options, token });
    } catch (error) {
      if (error.status === 401 && sessionStorage.getItem(tokenKey) === token) clearSession();
      throw error;
    }
  }, [token, clearSession]);

  useEffect(() => {
    if (!token || user) return;
    const controller = new AbortController();
    api("/api/auth/me", { signal: controller.signal })
      .then(profile => { if (!controller.signal.aborted) setUser(profile); })
      .catch(error => { if (!controller.signal.aborted && error.status !== 401) setBootError(error.message); });
    return () => controller.abort();
  }, [token, user, api, revision]);

  function login(session) {
    sessionStorage.setItem(tokenKey, session.access_token);
    setToken(session.access_token);
    setUser(session.user);
    setBootError("");
    setLogoutError("");
    window.location.hash = "/inicio";
  }

  async function logout() {
    setLogoutBusy(true);
    setLogoutError("");
    try {
      await api("/api/auth/logout", { method: "POST" });
      clearSession();
      window.location.hash = "/inicio";
    } catch (error) {
      if (error.status !== 401) setLogoutError(error.message);
    } finally {
      setLogoutBusy(false);
    }
  }

  if (!user) return <Login onLogin={login} restoring={Boolean(token && !bootError)} error={bootError}
    retry={() => { setBootError(""); setRevision(value => value + 1); }} />;

  return <Shell key={user.id} user={user} api={api} logout={logout} logoutBusy={logoutBusy} logoutError={logoutError} />;
}
