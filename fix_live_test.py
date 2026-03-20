import re

with open('/Users/wuliang/Workspace/self/pi-mono/python-packages/ai/test/live/test_friday_api_live.py', 'r') as f:
    content = f.read()

# Remove @pytest.mark.asyncio decorator lines inside class
content = re.sub(r'    @pytest\.mark\.asyncio\n', '', content)

# Remove fixture params from async/sync method signatures
content = re.sub(r'(    async def test_\w+)\(self, headers: Dict\[str, str\]\):', r'\1(self):', content)
content = re.sub(r'(    def test_\w+)\(self, config: Dict\[str, Any\]\):', r'\1(self):', content)
content = re.sub(r'(    def test_\w+)\(self, headers: Dict\[str, str\]\):', r'\1(self):', content)

# Replace bare 'headers' in API call arguments with 'self.headers'
content = re.sub(r'\(payload, headers\)', '(payload, self.headers)', content)
content = re.sub(r'\(payload_low_temp, headers\)', '(payload_low_temp, self.headers)', content)
content = re.sub(r'\(payload1, headers\)', '(payload1, self.headers)', content)
content = re.sub(r'\(payload2, headers\)', '(payload2, self.headers)', content)

# Fix test_config_file_valid body
old_valid = '''    def test_config_file_valid(self):
        """验证配置文件有效。"""
        assert "billing_id" in config, "配置应包含 billing_id"
        assert "agent_id" in config, "配置应包含 agent_id"
        assert config["billing_id"], "billing_id 不应为空"
        assert config["agent_id"], "agent_id 不应为空"

        print(f"\\n配置:")
        print(f"  billing_id: {config['billing_id']}")
        print(f"  agent_id: {config['agent_id']}")
        print(f"  api_url: {config.get('api_url', FRIDAY_API_URL)}")
        print(f"  default_model: {config.get('default_model', 'gpt-4o-mini')}")'''
new_valid = '''    def test_config_file_valid(self):
        """验证配置文件有效。"""
        raw = self.config.get("headers", self.config)
        assert raw.get("billing_id"), "billing_id 不应为空"
        assert raw.get("agent_id"), "agent_id 不应为空"

        print(f"\\n配置:")
        print(f"  billing_id: {raw['billing_id']}")
        print(f"  agent_id: {raw['agent_id']}")
        print(f"  api_url: {self.config.get('api_url', FRIDAY_API_URL)}")
        print(f"  default_model: {self.config.get('default_model', 'gpt-4o-mini')}")'''
content = content.replace(old_valid, new_valid)

# Fix test_headers_built_correctly body
content = content.replace('assert "Authorization" in headers', 'assert "Authorization" in self.headers')
content = content.replace('assert "Mt-Agent-Id" in headers', 'assert "Mt-Agent-Id" in self.headers')
content = content.replace('assert headers["Content-Type"]', 'assert self.headers["Content-Type"]')
content = content.replace('for k, v in headers.items()', 'for k, v in self.headers.items()')

with open('/Users/wuliang/Workspace/self/pi-mono/python-packages/ai/test/live/test_friday_api_live.py', 'w') as f:
    f.write(content)

print("done")

