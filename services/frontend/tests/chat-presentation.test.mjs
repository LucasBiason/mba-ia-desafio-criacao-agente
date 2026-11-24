import test from "node:test";
import assert from "node:assert/strict";
import { presentChatMessage } from "../src/chat-presentation.js";

const noise = "Nenhuma alteração foi registrada neste turno.";
const result = [
  {
    area_name: "Quadra poliesportiva",
    apartment: "101",
    date: "2030-04-06",
    fee_cents: 0,
    code: "RSV-Q",
    start_time: null,
    end_time: null,
  },
  {
    area_name: "Salão de festas",
    date: "2030-04-13",
    fee_cents: 15000,
    code: "RSV-S",
    start_time: "14:00",
    end_time: "17:30",
  },
];
const output =
  "Reservas ativas da sua unidade:\n" + JSON.stringify(result, null, 2);

test("converts an existing chat snapshot into display rows without leaking raw fields", () => {
  assert.deepEqual(presentChatMessage(noise + "\n" + output, "assistant"), {
    before: "",
    after: "",
    reservations: [
      {
        area: "Quadra poliesportiva",
        date: "06/04/2030",
        time: null,
        fee: 0,
        code: "RSV-Q",
      },
      {
        area: "Salão de festas",
        date: "13/04/2030",
        time: "14:00 às 17:30",
        fee: 15000,
        code: "RSV-S",
      },
    ],
  });
});

test("retains any separate text around the reservation snapshot", () => {
  const view = presentChatMessage(
    "Sobre a sua consulta\n\n" + output + "\n\nOutra resposta",
    "assistant",
  );
  assert.equal(view.before, "Sobre a sua consulta");
  assert.equal(view.after, "Outra resposta");
  assert.equal(view.reservations.length, 2);
});

test("removes only redundant assistant boilerplate and preserves user, safety and empty states", () => {
  for (const reply of [
    "Não há reservas ativas.",
    "Por privacidade, não posso consultar.",
    "A consulta falhou.",
    "Pedido pendente.",
  ]) {
    assert.deepEqual(presentChatMessage(noise + "\n" + reply, "assistant"), {
      text: reply,
    });
  }
  assert.equal(presentChatMessage(noise, "assistant").text, noise);
  assert.equal(
    presentChatMessage(noise + "\n" + output, "user").text,
    noise + "\n" + output,
  );
  assert.equal(
    presentChatMessage("Reserva gravada. Código: RSV-Q.", "assistant").text,
    "Reserva gravada. Código: RSV-Q.",
  );
});
