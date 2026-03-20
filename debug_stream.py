import asyncio
import os
from unittest.mock import MagicMock, AsyncMock, patch

from ai.core_types import Model, Context, UserMessage
from ai.providers.friday_config import FridayAuthConfig

basic_model = Model(id='gpt-4o-mini', name='GPT-4o Mini', api='friday-responses', provider='friday')
basic_context = Context(systemPrompt='test', messages=[UserMessage(content='hello', timestamp=1000)])
auth_config = FridayAuthConfig(billing_id='test_bid', agent_id='test_aid', user_id='test_uid')

events_data = [
    b'data: {"type": "response.created", "response": {}}\n',
    b'data: {"type": "response.output_item.added", "item": {"type": "message"}}\n',
    'data: {"type": "response.output_text.delta", "delta": "Hello"}\n'.encode('utf-8'),
    'data: {"type": "response.output_item.done", "item": {"type": "message", "content": [{"type": "output_text", "text": "Hello"}]}}\n'.encode('utf-8'),
    b'data: {"type": "response.completed", "response": {"status": "completed", "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}}}\n',
    b'data: [DONE]\n',
]

async def async_gen():
    for e in events_data:
        yield e

mock_response = MagicMock()
mock_response.status = 200
mock_response.content = async_gen()
mock_response.__aenter__ = AsyncMock(return_value=mock_response)
mock_response.__aexit__ = AsyncMock(return_value=False)

mock_post_cm = MagicMock()
mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
mock_post_cm.__aexit__ = AsyncMock(return_value=False)

mock_session = MagicMock()
mock_session.post = MagicMock(return_value=mock_post_cm)
mock_session.__aenter__ = AsyncMock(return_value=mock_session)
mock_session.__aexit__ = AsyncMock(return_value=False)

mock_session_cls = MagicMock(return_value=mock_session)

async def run():
    from ai.providers.friday_responses import stream_friday_responses
    with patch('aiohttp.ClientSession', mock_session_cls):
        with patch.dict(os.environ, {'FRIDAY_BILLING_ID': auth_config.billing_id, 'FRIDAY_AGENT_ID': auth_config.agent_id or ''}):
            stream = stream_friday_responses(basic_model, basic_context)
            events = []
            async for event in stream:
                events.append(event)
    print('event types:', [e.type for e in events])
    from ai.core_types import TextDeltaEvent, DoneEvent
    text_deltas = [e for e in events if isinstance(e, TextDeltaEvent)]
    print('text_deltas:', text_deltas)

asyncio.run(run())

