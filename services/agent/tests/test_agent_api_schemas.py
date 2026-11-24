"""Pure DTO tests: no API startup, persistence, environment or model access."""

import unittest
from datetime import date

from pydantic import ValidationError

from services.agent.api.schemas import (
    ConfirmationInput,
    EventsResponse,
    MessageInput,
    MessageResponse,
    PendingConfirmation,
    ReservationRead,
    SessionInput,
    SessionResponse,
    VisitorRead,
)


class AcademicSchemasTest(unittest.TestCase):
    def test_official_examples_roundtrip_without_added_keys(self):
        cases = (
            (SessionInput, {"apartamento": "101"}),
            (MessageInput, {"texto": "Reserve a quadra"}),
            (ConfirmationInput, {"id": "confirmation", "confirmado": True}),
            (SessionResponse, {"session_id": "session"}),
            (
                ReservationRead,
                {"codigo": "RSV-1377", "area": "quadra", "data": "2030-03-09"},
            ),
            (VisitorRead, {"nome": "Marina Duarte", "data": "2030-03-16"}),
        )
        for model, payload in cases:
            with self.subTest(model=model.__name__):
                self.assertEqual(
                    model.model_validate(payload).model_dump(mode="json"), payload
                )
                with self.assertRaises(ValidationError):
                    model.model_validate({**payload, "internal": "not public"})

    def test_confirmation_boolean_has_no_coercion(self):
        for value in ("true", "false", 0, 1, None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                ConfirmationInput(id="confirmation", confirmado=value)

    def test_strings_have_no_coercion(self):
        for model, payload in (
            (SessionInput, {"apartamento": 101}),
            (MessageInput, {"texto": b"text"}),
            (SessionResponse, {"session_id": 12}),
            (VisitorRead, {"nome": "Visitor", "data": date(2030, 3, 16)}),
        ):
            with self.subTest(model=model.__name__), self.assertRaises(ValidationError):
                model.model_validate(payload)

    def test_empty_reply_and_arbitrary_nested_details_are_preserved(self):
        payload = {
            "resposta": "",
            "confirmacoes_pendentes": [
                {
                    "id": "x",
                    "acao": "future-action",
                    "detalhes": {
                        "unrestricted": [1, True, None, {"nested": "value"}],
                        "amount": 12.5,
                    },
                }
            ],
        }
        self.assertEqual(
            MessageResponse.model_validate(payload).model_dump(mode="json"), payload
        )
        with self.assertRaises(ValidationError):
            MessageResponse.model_validate({**payload, "debug": True})
        with self.assertRaises(ValidationError):
            PendingConfirmation(id="x", acao="action", detalhes=[])

    def test_required_response_envelope_cannot_be_omitted(self):
        for payload in ({"resposta": "ok"}, {"confirmacoes_pendentes": []}):
            with self.assertRaises(ValidationError):
                MessageResponse.model_validate(payload)

    def test_date_format_and_calendar_are_validated(self):
        for value in ("2030-3-09", "2030-02-30", "2030-03-09T12:00:00", "tomorrow"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                VisitorRead(nome="Visitor", data=value)

    def test_events_preserve_complete_arbitrary_json_and_order(self):
        events = [{"event": 2, "payload": {"unknown": [None, True, 2.5]}}, {"event": 1}]
        self.assertEqual(
            EventsResponse.model_validate(events).model_dump(mode="json"), events
        )
        for payload in ({"events": events}, ["not an object"], [{"data": object()}]):
            with self.assertRaises(ValidationError):
                EventsResponse.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
