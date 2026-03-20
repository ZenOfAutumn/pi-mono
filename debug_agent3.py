"""调试：确认错误被正确捕获并反映在 content 中。"""
import asyncio
import json
from pathlib import Path

from ai.core_types import Model, Context, UserMessage
from ai.providers.friday_config import FridayResponsesOptions
from ai.providers.friday_responses import stream_friday_responses


async def main():
    config_file = Path("python-packages/ai/config/friday.json")
    with open(config_file) as f:
        config = json.load(f)
    raw = config.get("headers", config)
    options: FridayResponsesOptions = {"billingId": raw["billing_id"]}
    if raw.get("agent_id"):
        options["agentId"] = raw["agent_id"]

    model = Model(id='gpt-4o', name='GPT-4o', api='friday-responses', provider='friday')
    context = Context(
        systemPrompt="You are a helpful assistant.",
        messages=[UserMessage(content="Say 'Hello from agent test' and nothing else", timestamp=1000)],
    )

    stream = stream_friday_responses(model, context, options)
    async for event in stream:
        print(f"event.type={event.type!r}")
        if event.type == "error":
            print(f"  error message: {event.error.errorMessage!r}")
        elif event.type == "done":
            print(f"  content: {event.message.content!r}")

asyncio.run(main())

