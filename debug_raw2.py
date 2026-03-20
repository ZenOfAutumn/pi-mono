import asyncio
import json
from pathlib import Path
import aiohttp

config_file = Path("python-packages/ai/config/friday.json")
with open(config_file) as f:
    config = json.load(f)
raw = config.get("headers", config)

headers = {
    "Content-Type": "application/json;charset=UTF-8",
    "Authorization": f"Bearer {raw['billing_id']}",
}
if raw.get("agent_id"):
    headers["Mt-Agent-Id"] = raw["agent_id"]

from ai.providers.friday_responses import convert_messages_to_friday
from ai.core_types import Model, Context, UserMessage
from ai.providers.friday_config import FRIDAY_RESPONSES_API_URL

model = Model(id='gpt-4o', name='GPT-4o', api='friday-responses', provider='friday')
context = Context(
    systemPrompt="You are a helpful assistant.",
    messages=[UserMessage(content="Say 'Hello from agent test' and nothing else", timestamp=1000)],
)

messages = convert_messages_to_friday(context, model)
payload = {
    "model": model.id,
    "input": messages,
    "stream": True,
}
if context.systemPrompt:
    payload["instructions"] = context.systemPrompt

async def run():
    async with aiohttp.ClientSession() as session:
        async with session.post(FRIDAY_RESPONSES_API_URL, headers=headers, json=payload) as response:
            print(f"status: {response.status}")
            async for line in response.content:
                line_text = line.decode("utf-8").strip()
                if line_text:
                    print(repr(line_text[:300]))

asyncio.run(run())

