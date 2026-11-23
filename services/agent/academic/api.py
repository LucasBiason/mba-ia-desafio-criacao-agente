"""Exact academic API, deliberately not mounted in the authenticated product."""

from contextlib import asynccontextmanager
import asyncio
from weakref import WeakValueDictionary
import json
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from services.agent.academic.schemas import (
    SessionInput,
    MessageInput,
    ConfirmationInput,
    SessionResponse,
    MessageResponse,
    ReservationRead,
    VisitorRead,
    EventsResponse,
)
from google.adk.sessions import DatabaseSessionService
from google.adk.sessions.base_session_service import GetSessionConfig
from google.genai import types
from services.agent.academic.runtime import AcademicRuntime, APP_NAME, USER_ID


_SQLITE_TURNS: WeakValueDictionary[tuple[str, str], asyncio.Lock] = (
    WeakValueDictionary()
)


def prepare_domain_tables(domain):
    """Prepare the portable academic API schema before multiple replicas start."""
    with domain.connection(write=True) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS academic_sessions (id TEXT PRIMARY KEY, apartment TEXT NOT NULL)"
        )
        conn.execute("""CREATE TABLE IF NOT EXISTS academic_confirmations (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL, invocation TEXT NOT NULL,
            payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending')""")
        conn.execute("""CREATE TABLE IF NOT EXISTS academic_confirmation_outcomes (
            confirmation_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, apartment TEXT NOT NULL,
            operation_id TEXT NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL, result TEXT)""")


def create_app(*, domain, session_url, models, regulation, replica_id=None):
    """Dependencies are explicit; initialize fixtures separately, never on startup."""
    postgres = getattr(domain, "is_postgres", False)
    prefix = "postgresql+psycopg://" if postgres else "sqlite+aiosqlite:///"
    if ":memory:" in session_url or not session_url.startswith(prefix):
        raise ValueError(
            "Academic sessions require a persistent store matching the domain backend."
        )
    if not postgres:
        prepare_domain_tables(domain)
    sessions = DatabaseSessionService(db_url=session_url)

    @asynccontextmanager
    async def lifespan(app):
        try:
            if postgres:
                # The init job migrates once. Warm up each replica on the existing schema.
                await sessions.prepare_tables()
                with domain.connection() as conn:
                    conn.execute("SELECT id FROM academic_sessions LIMIT 0")
                    conn.execute("SELECT id FROM academic_confirmations LIMIT 0")
            yield
        finally:
            await sessions.close()

    app = FastAPI(title="Aurora · avaliação acadêmica isolada", lifespan=lifespan)
    app.state.session_service = sessions

    if replica_id:

        @app.middleware("http")
        async def identify_replica(request, call_next):
            response = await call_next(request)
            response.headers["X-Aurora-Replica"] = replica_id
            return response

    @asynccontextmanager
    async def session_turn(session_id):
        if not postgres:
            # SQLite profile is one process. Share active locks across app objects
            # using the same persisted store, including restart-style test clients.
            key = (session_url, session_id)
            lock = _SQLITE_TURNS.setdefault(key, asyncio.Lock())
            if lock.locked():
                raise HTTPException(409, "Há um turno em execução nesta sessão.")
            async with lock:
                yield
            return
        async with domain.try_session_turn(session_id) as acquired:
            if not acquired:
                raise HTTPException(
                    409,
                    "Já existe um turno em execução nesta sessão; consulte eventos e projeções.",
                )
            yield

    def apartment_for(session_id):
        with domain.connection() as conn:
            row = conn.execute(
                "SELECT apartment FROM academic_sessions WHERE id=?", (session_id,)
            ).fetchone()
        if not row:
            raise HTTPException(404, "Sessão não encontrada.")
        return row["apartment"]

    def reconcile_interrupted(session_id, apartment):
        """Under turn ownership, terminalize abandoned work without running a tool.

        A missing receipt is fenced atomically with an interrupted receipt using
        the original operation identity. A delayed invocation can only replay that
        terminal outcome, never perform its effect. Divergent evidence stays blocked.
        """

        def decode(value):
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError):
                raise HTTPException(
                    409, "Evidência inválida; reconciliação bloqueada."
                ) from None
            if not isinstance(parsed, dict):
                raise HTTPException(409, "Evidência inválida; reconciliação bloqueada.")
            return parsed

        with domain.connection(write=True) as conn:
            abandoned = conn.execute(
                "SELECT id,payload FROM academic_confirmations WHERE session_id=? AND status='processing'",
                (session_id,),
            ).fetchall()
            for item in abandoned:
                binding = conn.execute(
                    "SELECT * FROM academic_confirmation_outcomes WHERE confirmation_id=? AND session_id=? AND apartment=?",
                    (item["id"], session_id, apartment),
                ).fetchone()
                payload = decode(item["payload"])
                if (
                    not binding
                    or binding["action"] not in ("reservar_area", "autorizar_visitante")
                    or binding["action"] != payload.get("acao")
                    or decode(binding["payload"]) != payload.get("detalhes")
                    or not isinstance(binding["operation_id"], str)
                    or not binding["operation_id"]
                ):
                    raise HTTPException(
                        409, "Confirmação interrompida exige verificação do vínculo."
                    )
                action = (
                    "paid_reservation"
                    if binding["action"] == "reservar_area"
                    else "autorizar_visitante"
                )
                details = decode(binding["payload"])
                receipt = conn.execute(
                    "SELECT * FROM receipts WHERE operation_id=?",
                    (binding["operation_id"],),
                ).fetchone()
                recorded = (
                    decode(binding["result"]) if binding["result"] is not None else None
                )
                if receipt is None:
                    if recorded is not None and recorded not in (
                        {"status": "rejected"},
                        {"status": "interrupted"},
                    ):
                        raise HTTPException(
                            409,
                            "Resultado sem recibo correspondente; reconciliação bloqueada.",
                        )
                    # Use the same operation fence as real writes. On PostgreSQL
                    # this also serializes a detached late runner on the operation ID.
                    result = domain._once(
                        conn,
                        apartment,
                        action,
                        details,
                        binding["operation_id"],
                        lambda: recorded or {"status": "interrupted"},
                    )
                else:
                    if (
                        receipt["apartment"] != apartment
                        or receipt["action"] != action
                        or decode(receipt["payload"]) != details
                    ):
                        raise HTTPException(
                            409, "Recibo divergente; confirmação não reconciliada."
                        )
                    result = decode(receipt["result"])
                if recorded is not None and recorded != result:
                    raise HTTPException(
                        409,
                        "Resultado divergente do recibo; reconciliação bloqueada.",
                    )
                allowed = (
                    {
                        "reserved",
                        "occupied",
                        "policy_denied",
                        "policy_changed",
                        "interrupted",
                        "rejected",
                    }
                    if action == "paid_reservation"
                    else {"authorized", "interrupted", "rejected"}
                )
                if not isinstance(result, dict) or result.get("status") not in allowed:
                    raise HTTPException(
                        409, "Resultado divergente; confirmação não reconciliada."
                    )
                conn.execute(
                    "UPDATE academic_confirmation_outcomes SET result=? WHERE confirmation_id=? AND session_id=? AND apartment=?",
                    (
                        json.dumps(result, ensure_ascii=False),
                        item["id"],
                        session_id,
                        apartment,
                    ),
                )
                conn.execute(
                    "UPDATE academic_confirmations SET status='consumed' WHERE id=? AND session_id=? AND status='processing'",
                    (item["id"], session_id),
                )

    def pending(session_id):
        with domain.connection() as conn:
            rows = conn.execute(
                "SELECT id,payload FROM academic_confirmations WHERE session_id=? AND status='pending' ORDER BY id",
                (session_id,),
            ).fetchall()
        return [{"id": r["id"], **json.loads(r["payload"])} for r in rows]

    def collect(session_id, events):
        with domain.connection(write=True) as conn:
            for event in events:
                for call in event.get_function_calls():
                    if call.name == "adk_request_confirmation":
                        # Only ADK's generated long-running request is eligible; a model
                        # spelling the function name cannot manufacture a confirmation.
                        args = call.args if isinstance(call.args, dict) else {}
                        original = args.get("originalFunctionCall", {})
                        confirmation = args.get("toolConfirmation", {})
                        payload = (
                            confirmation.get("payload")
                            if isinstance(confirmation, dict)
                            else None
                        )
                        if (
                            call.id not in (event.long_running_tool_ids or [])
                            or not isinstance(original, dict)
                            or not isinstance(payload, dict)
                            or set(payload) != {"acao", "detalhes"}
                            or payload.get("acao")
                            not in ("reservar_area", "autorizar_visitante")
                            or original.get("name") != payload.get("acao")
                            or not isinstance(original.get("id"), str)
                            or not 1 <= len(original["id"]) <= 256
                            or not isinstance(payload.get("detalhes"), dict)
                        ):
                            continue
                        conn.execute(
                            "INSERT INTO academic_confirmations(id,session_id,invocation,payload) VALUES(?,?,?,?) ON CONFLICT(id) DO NOTHING",
                            (
                                call.id,
                                session_id,
                                event.invocation_id,
                                json.dumps(payload, ensure_ascii=False),
                            ),
                        )
                        apartment = conn.execute(
                            "SELECT apartment FROM academic_sessions WHERE id=?",
                            (session_id,),
                        ).fetchone()["apartment"]
                        conn.execute(
                            """INSERT INTO academic_confirmation_outcomes
                            (confirmation_id,session_id,apartment,operation_id,action,payload)
                            VALUES(?,?,?,?,?,?) ON CONFLICT(confirmation_id) DO NOTHING""",
                            (
                                call.id,
                                session_id,
                                apartment,
                                original["id"],
                                payload["acao"],
                                json.dumps(
                                    payload["detalhes"],
                                    ensure_ascii=False,
                                    sort_keys=True,
                                    separators=(",", ":"),
                                ),
                            ),
                        )
        text = "\n".join(
            part.text
            for event in events
            if event.author != "user" and event.is_final_response() and event.content
            for part in event.content.parts or []
            if part.text and not part.thought
        )
        return {"resposta": text, "confirmacoes_pendentes": pending(session_id)}

    async def recover_orphan_proposal(session_id, confirmation_id):
        """Exact-ID repair on demand, never a full-history scan or implicit approval.

        Only the most recent 100 persisted events are inspected. Missing/truncated
        provenance is not guessed; the caller receives the ordinary 409.
        """
        with domain.connection() as conn:
            known = conn.execute(
                "SELECT id FROM academic_confirmations WHERE id=?", (confirmation_id,)
            ).fetchone()
        if known:
            return  # Includes consumed, foreign and processing IDs: never resurrect.
        session = await sessions.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
            config=GetSessionConfig(num_recent_events=100),
        )
        if session is None:
            return
        events = session.events
        if any(
            response.name == "adk_request_confirmation"
            and response.id == confirmation_id
            for event in events
            for response in event.get_function_responses()
        ):
            return  # A decision already entered ADK; absence of an API row is ambiguous.
        candidates = []
        for event in events:
            if (
                event.author not in ("reservas", "convivencia")
                or not event.content
                or event.content.role != "model"
            ):
                continue
            for call in event.get_function_calls():
                if (
                    call.id != confirmation_id
                    or call.name != "adk_request_confirmation"
                    or call.id not in (event.long_running_tool_ids or [])
                ):
                    continue
                original = (
                    call.args.get("originalFunctionCall")
                    if isinstance(call.args, dict)
                    else None
                )
                if not isinstance(original, dict) or original.get("name") not in (
                    "reservar_area",
                    "autorizar_visitante",
                ):
                    continue
                proven_call = any(
                    prior.invocation_id == event.invocation_id
                    and prior.author == event.author
                    and prior.content
                    and prior.content.role == "model"
                    and source.id == original.get("id")
                    and source.name == original.get("name")
                    and source.args == original.get("args")
                    for prior in events
                    for source in prior.get_function_calls()
                )
                if proven_call:
                    candidates.append((event, original.get("id")))
        if len(candidates) != 1:
            return
        event, operation_id = candidates[0]
        with domain.connection() as conn:
            if conn.execute(
                "SELECT operation_id FROM receipts WHERE operation_id=?",
                (operation_id,),
            ).fetchone():
                return  # A durable effect is not a fresh pending proposal.
        collect(session_id, [event])  # Reuse strict payload/ADK metadata validation.

    def authoritative_writes(apartment, events):
        """Use executed tool events/receipts, never classify the user's prose.

        Successful mutations require a committed receipt with matching tool ID,
        apartment, action and canonical area/date. Negative prechecks require an
        ADK tool response (role=user), paired to its call in this invocation.
        """
        calls = {}
        results = []
        writes = {
            "reservar_area": "free_reservation",
            "cancelar_reserva": "cancel_reservation",
        }
        negatives = {
            "occupied",
            "not_found",
            "unknown_area",
            "invalid_date",
            "time_not_supported",
            "invalid_policy_input",
            "policy_denied",
            "policy_changed",
            "operation_conflict",
            "manual_attendance_required",
            "pending_external_confirmation",
        }
        for event in events:
            if not event.content or event.author != "reservas":
                continue
            if event.content.role == "model":
                for call in event.get_function_calls():
                    if call.name in writes and call.id and isinstance(call.args, dict):
                        calls[(event.invocation_id, call.id)] = call
            if event.content.role != "user":
                continue
            for response in event.get_function_responses():
                call = calls.get((event.invocation_id, response.id))
                if call is None or response.name != call.name:
                    continue
                result = None
                with domain.connection() as conn:
                    receipt = conn.execute(
                        "SELECT * FROM receipts WHERE operation_id=?", (call.id,)
                    ).fetchone()
                    if receipt:
                        payload = json.loads(receipt["payload"])
                        area = domain._area(conn, call.args.get("area"))
                        valid = (
                            receipt["apartment"] == apartment
                            and receipt["action"] == writes[call.name]
                            and area is not None
                            and payload.get("area") == area["id"]
                            and payload.get("data") == call.args.get("data")
                        )
                        for field in ("hora_inicio", "hora_fim"):
                            if (
                                call.args.get(field)
                                and payload.get(field) != call.args[field]
                            ):
                                valid = False
                        if valid:
                            result = json.loads(receipt["result"])
                    elif (
                        isinstance(response.response, dict)
                        and response.response.get("status") in negatives
                    ):
                        result = dict(response.response)
                if not isinstance(result, dict) or not isinstance(
                    result.get("status"), str
                ):
                    raise HTTPException(
                        503,
                        "Operação sem resultado comprovado; consulte eventos e projeções.",
                    )
                results.append(result)
        if calls and len(results) != len(calls):
            raise HTTPException(
                503, "Execução de ferramenta incompleta; consulte eventos e projeções."
            )
        if not calls:
            return None
        labels = {
            "reserved": "Reserva gravada.",
            "cancelled": "Reserva própria cancelada.",
            "occupied": "Não foi possível reservar: área ocupada.",
            "not_found": "Nenhuma reserva própria correspondente foi encontrada.",
            "policy_denied": "Operação não realizada: regras não permitem este pedido.",
            "policy_changed": "Operação não realizada: política alterada, revise o pedido.",
            "pending_external_confirmation": "Pedido pendente; confirme pela rota de confirmações.",
            "manual_attendance_required": "Operação não realizada; atendimento manual necessário.",
        }
        results = [
            {
                **r,
                "mensagem": labels.get(
                    r["status"], "Operação não realizada; revise os dados do pedido."
                ),
            }
            for r in results
        ]
        value = (
            results[0]
            if len(results) == 1
            else {"status": "multiple_results", "resultados": results}
        )
        return json.dumps(value, ensure_ascii=False)

    async def run(session_id, message, invocation=None):
        apartment = apartment_for(session_id)
        runtime = AcademicRuntime(domain, apartment, models, sessions, regulation)
        try:
            return await runtime.run(session_id, message, invocation)
        except Exception as exc:
            # Provider exception messages/requests may contain credentials; never return them.
            code = 429 if getattr(exc, "code", None) == 429 else 503
            raise HTTPException(
                code,
                "Quota do modelo esgotada."
                if code == 429
                else "Execução indisponível; consulte eventos antes de repetir.",
            ) from None

    @app.post("/sessoes", status_code=201, response_model=SessionResponse)
    async def create_session(data: SessionInput):
        if not domain.has_apartment(data.apartamento):
            raise HTTPException(422, "Apartamento desconhecido.")
        sid = str(uuid4())
        await sessions.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=sid,
            state={"apartamento": data.apartamento},
        )
        with domain.connection(write=True) as conn:
            conn.execute(
                "INSERT INTO academic_sessions VALUES(?,?)", (sid, data.apartamento)
            )
        return {"session_id": sid}

    @app.post("/sessoes/{session_id}/mensagens", response_model=MessageResponse)
    async def message(session_id: str, data: MessageInput):
        async with session_turn(session_id):
            apartment = apartment_for(session_id)
            if not data.texto.strip():
                raise HTTPException(422, "Mensagem vazia.")
            reconcile_interrupted(session_id, apartment)
            with domain.connection() as conn:
                unresolved = conn.execute(
                    "SELECT 1 FROM academic_confirmations WHERE session_id=? AND status IN ('pending','processing')",
                    (session_id,),
                ).fetchone()
            if unresolved:
                raise HTTPException(
                    409,
                    "Há confirmação pendente ou em processamento; consulte eventos e projeções.",
                )
            events = await run(
                session_id,
                types.Content(role="user", parts=[types.Part(text=data.texto)]),
            )
            response = collect(session_id, events)
            try:
                authoritative = authoritative_writes(apartment_for(session_id), events)
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(
                    503,
                    "Não foi possível verificar o resultado; consulte eventos e projeções.",
                ) from None
            if authoritative is not None:
                response["resposta"] = authoritative
            return response

    @app.post("/sessoes/{session_id}/confirmacoes", response_model=MessageResponse)
    async def confirm(session_id: str, data: ConfirmationInput):
        async with session_turn(session_id):
            apartment = apartment_for(session_id)
            await recover_orphan_proposal(session_id, data.id)
            with domain.connection(write=True) as conn:
                row = conn.execute(
                    """UPDATE academic_confirmations SET status='processing'
                    WHERE id=? AND session_id=? AND status='pending' RETURNING invocation,payload""",
                    (data.id, session_id),
                ).fetchone()
                if row is None:
                    raise HTTPException(
                        409, "Confirmação não está pendente nesta sessão."
                    )
            payload = json.loads(row["payload"])
            content = types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            name="adk_request_confirmation",
                            id=data.id,
                            response={"confirmed": data.confirmado, "payload": payload},
                        )
                    )
                ],
            )
            # The model is not the source of truth for an executed action. Even if
            # its final response fails, recover only a committed, exactly scoped receipt.
            execution_error = None
            completed_events = []
            try:
                completed_events = await run(session_id, content, row["invocation"])
            except HTTPException as exc:
                execution_error = exc
            if completed_events:
                collect(
                    session_id, completed_events
                )  # Keep subsequent ADK pending requests, not its success text.
            with domain.connection(write=True) as conn:
                binding = conn.execute(
                    """SELECT * FROM academic_confirmation_outcomes
                    WHERE confirmation_id=? AND session_id=? AND apartment=?""",
                    (data.id, session_id, apartment),
                ).fetchone()
                result = None
                if (
                    binding
                    and binding["action"] == payload["acao"]
                    and json.loads(binding["payload"]) == payload["detalhes"]
                ):
                    receipt = conn.execute(
                        "SELECT * FROM receipts WHERE operation_id=?",
                        (binding["operation_id"],),
                    ).fetchone()
                    expected_action = (
                        "paid_reservation"
                        if binding["action"] == "reservar_area"
                        else "autorizar_visitante"
                    )
                    if (
                        receipt
                        and (receipt["apartment"], receipt["action"])
                        == (binding["apartment"], expected_action)
                        and json.loads(receipt["payload"])
                        == json.loads(binding["payload"])
                    ):
                        if data.confirmado:
                            candidate = json.loads(receipt["result"])
                            permitted = (
                                {
                                    "reserved",
                                    "occupied",
                                    "policy_denied",
                                    "policy_changed",
                                }
                                if binding["action"] == "reservar_area"
                                else {"authorized"}
                            )
                            if candidate.get("status") in permitted:
                                result = candidate
                    elif receipt is None and not data.confirmado:
                        result = {"status": "rejected"}
                if result is None:
                    # No proven effect: preserve processing, never execute/retry here.
                    raise execution_error or HTTPException(
                        503,
                        "Resultado não comprovado; consulte eventos e projeções antes de qualquer nova ação.",
                    )
                conn.execute(
                    "UPDATE academic_confirmation_outcomes SET result=? WHERE confirmation_id=? AND session_id=?",
                    (json.dumps(result, ensure_ascii=False), data.id, session_id),
                )
                conn.execute(
                    "UPDATE academic_confirmations SET status='consumed' WHERE id=? AND session_id=?",
                    (data.id, session_id),
                )
            messages = {
                "reserved": "Reserva confirmada e gravada.",
                "occupied": "Não foi possível reservar: área ocupada nesta data.",
                "policy_denied": "Reserva não realizada: as regras aplicáveis não permitem este pedido.",
                "policy_changed": "Reserva não realizada: a política mudou; revise o pedido.",
                "authorized": "Autorização de visitante gravada.",
                "rejected": "Pedido negado; nenhuma alteração realizada.",
            }
            # JSON text remains compatible with structured fake benchmarks; the
            # Portuguese message is deterministic, not generated by the model.
            authoritative = {**result, "mensagem": messages[result["status"]]}
            return {
                "resposta": json.dumps(authoritative, ensure_ascii=False),
                "confirmacoes_pendentes": pending(session_id),
            }

    @app.get("/sessoes/{session_id}/eventos", response_model=EventsResponse)
    async def events(session_id: str):
        apartment_for(session_id)
        session = await sessions.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
        if session is None:
            raise HTTPException(503, "Histórico indisponível.")
        return [
            event.model_dump(mode="json", exclude_none=True) for event in session.events
        ]

    @app.get("/apartamentos/{numero}/reservas", response_model=list[ReservationRead])
    async def reservations(numero: str):
        return domain.reservations(numero)

    @app.get("/apartamentos/{numero}/visitantes", response_model=list[VisitorRead])
    async def visitors(numero: str):
        return domain.visitors(numero)

    return app
