import asyncio
import json
from pathlib import Path

from ai.core_types import Model, Context, UserMessage
from ai.providers.friday_config import FridayResponsesOptions
from ai.providers.friday_responses import stream_friday_responses
from ai.core_types import TextDeltaEvent, DoneEvent, ErrorEvent

config_file = Path("config/friday.json")
with open(config_file) as f:
    config = json.load(f)

raw = config.get("headers", config)
billing_id = raw.get("billing_id")
agent_id = raw.get("agent_id")

basic_model = Model(id='gpt-4o-mini', name='GPT-4o Mini', api='friday-responses', provider='friday')
basic_context = Context(systemPrompt='你是一个有帮助的助手。', messages=[UserMessage(content='你好，请介绍一下自己。', timestamp=1000)])

options: FridayResponsesOptions = {"billingId": billing_id}
if agent_id:
    options["agentId"] = agent_id

async def run():
    stream = stream_friday_responses(basic_model, basic_context, options)
    events = []
    async for event in stream:
        events.append(event)
        print(f"event: {event.type}")
    print(f"total events: {len(events)}")
    text_deltas = [e for e in events if isinstance(e, TextDeltaEvent)]
    print(f"text_delta count: {len(text_deltas)}")
    done_events = [e for e in events if isinstance(e, DoneEvent)]
    print(f"done count: {len(done_events)}")
    error_events = [e for e in events if isinstance(e, ErrorEvent)]
    print(f"error count: {len(error_events)}")
    if error_events:
        print(f"error: {error_events[0].error.errorMessage}")

asyncio.run(run())

