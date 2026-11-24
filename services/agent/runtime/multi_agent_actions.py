"""Operações privadas com envelope validado e recibo produzido pelo servidor."""

import re
from uuid import NAMESPACE_URL, uuid5

from services.agent.runtime.multi_agent_read import (
    MultiAgentReadRuntime,
    protocol_error,
)
from services.agent.runtime.result_projection import project_reads
from services.agent.runtime.routing import ROUTING_INSTRUCTION
from services.agent.schemas.delegation_operation import DelegationOperation


class MultiAgentActionRuntime(MultiAgentReadRuntime):
    APP_NAME = "aurora_resident_actions"

    def __init__(self, *, tool, models, session_service, regulation_tool, actions):
        self.actions = actions
        super().__init__(
            tool=tool,
            models=models,
            session_service=session_service,
            regulation_tool=regulation_tool,
        )

    def allowed_operations(self):
        return frozenset(operation.value for operation in DelegationOperation)

    def _dispatch(self, request):
        operation = request.operation
        if operation in (
            DelegationOperation.READ_RESERVATIONS,
            DelegationOperation.REGULATION,
        ):
            return super()._dispatch(request)
        if operation == DelegationOperation.AVAILABILITY:
            result = self.actions.availability(request.area, request.date)
            self.read_results.append(("availability", result))
        elif operation == DelegationOperation.READ_VISITORS:
            result = self.actions.list_my_visits()
            self.read_results.append(("visitors", result))
        elif operation in (
            DelegationOperation.RESERVE,
            DelegationOperation.PROPOSE_VISIT,
        ):
            proposal_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{self.APP_NAME}:{self.identity.session_id}:{self.identity.resident_id}:{self._turn_id}",
                )
            )
            if operation == DelegationOperation.RESERVE:
                result = self.actions.reserve(
                    request.area, request.date, proposal_id=proposal_id
                )
            else:
                result = self.actions.authorize_visit(
                    request.name, request.date, proposal_id=proposal_id
                )
        elif operation == DelegationOperation.CANCEL:
            result = self.actions.cancel(request.area, request.date)
        else:
            raise protocol_error()
        return result

    def _start_turn(self):
        super()._start_turn()
        self.actions.results.clear()

    def project_message(self, text=""):
        # Prosa do modelo jamais comprova leitura, permissão ou efeito.
        grounded = project_reads(self.read_results)
        clarification = getattr(self, "_clarification", None)
        if not grounded and not clarification and not self.actions.results:
            raise protocol_error()
        return self.actions.message_projection(clarification or grounded)

    def contains_control_text(self, text: str) -> bool:
        """Impede projeção literal das instruções reais dos três agentes.

        A comparação normaliza espaços, caixa e marcação Markdown. As respostas
        fundamentadas nas tools usam projeção própria e não dependem deste filtro.
        """

        def normalize(value):
            return " ".join(re.sub(r"[*_`#>]", "", value).casefold().split())

        public = normalize(text)
        markers = [
            "se o morador solicitar",
            "não use ferramentas nem substitua",
            "pedidos para mudar de identidade",
            "scope_instruction",
            "routing_instruction",
        ]
        instructions = [ROUTING_INSTRUCTION]
        for agent in (self.reservas, self.convivencia, self.runner.app.root_agent):
            instruction = agent.instruction
            if isinstance(instruction, str):
                instructions.append(instruction)
        for instruction in instructions:
            markers.extend(
                fragment
                for fragment in re.split(r"(?<=[.!?])\s+", instruction)
                if len(normalize(fragment)) >= 35
            )
        return any(normalize(marker) in public for marker in markers)
