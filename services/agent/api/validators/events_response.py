from pydantic import ConfigDict, JsonValue, RootModel


class EventsResponse(RootModel[list[dict[str, JsonValue]]]):
    """Ordered raw JSON event objects; no filtering or ADK-specific schema."""

    model_config = ConfigDict(strict=True, hide_input_in_errors=True)
