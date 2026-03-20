import asyncio
import json
from pathlib import Path
import aiohttp

config_file = Path("python-packages/ai/config/friday.json")
with open(config_file) as f:
    config = json.load(f)

raw = config.get("headers", config)
billing_id = raw.get("billing_id")
agent_id = raw.get("agent_id")

headers = {
    "Content-Type": "application/json;charset=UTF-8",
    "Authorization": f"Bearer {billing_id}",
}
if agent_id:
    headers["Mt-Agent-Id"] = agent_id

payload = {
    "model": "gpt-4o-mini",
    "input": [{"role": "user", "content": [{"type": "input_text", "text": "你好"}]}],
    "stream": True,
}

async def run():
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://aigc.sankuai.com/v1/responses",
            headers=headers,
            json=payload,
        ) as response:
            print(f"status: {response.status}")
            count = 0
            async for line in response.content:
                line_text = line.decode("utf-8").strip()
                if line_text:
                    print(repr(line_text[:200]))
                count += 1
                if count > 20:
                    break

asyncio.run(run())

