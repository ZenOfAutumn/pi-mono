"""调试：追踪 output.content 的变化时机。"""
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
        system_prompt="You are a helpful assistant.",
        messages=[UserMessage(content="Say 'Hello from agent test' and nothing else", timestamp=1000)],
    )

    stream = stream_friday_responses(model, context, options)

    start_partial = None
    async for event in stream:
        etype = event.type
        if etype == "start":
            start_partial = event.partial
            print(f"start: partial.content = {start_partial.content!r}")
            print(f"start: id(partial.content) = {id(start_partial.content)}")
        elif etype == "text_start":
            print(f"text_start: partial.content = {event.partial.content!r}")
        elif etype == "text_delta":
            print(f"text_delta: delta={event.delta!r}, partial.content len={len(event.partial.content)}")
            if event.partial.content:
                print(f"  content[0]['text'] = {event.partial.content[0].get('text', '')!r}")
        elif etype == "done":
            print(f"\ndone: message.content = {event.message.content!r}")
            print(f"done: id(message.content) = {id(event.message.content)}")
            if start_partial:
                print(f"\nstart_partial.content after done: {start_partial.content!r}")
                print(f"same object? {start_partial is event.message}")

asyncio.run(main())

