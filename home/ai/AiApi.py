import enum

from openai import OpenAI

DEEPSEEK_API_KEY = "sk-e0c105badff24bdc8f89efa12e7bbb7d"

class AiType(enum.Enum):
    DEEPSEEK = 0, DEEPSEEK_API_KEY


class AiApi(object):
    def query(self, query: str, system_prompt="You are a helpful assistant", think: bool = True) -> str:
        pass


class _DeepSeekApi(AiApi):
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1"
        self.client: OpenAI = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url)

    def query(self, query: str, system_prompt="You are a helpful assistant", think: bool = True) -> str:
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            model='deepseek-reasoner' if think else 'deepseek-chat',
            stream=False
        )

        return response.choices[0].message.content


class AiApiFactory:
    deep_seek_api: _DeepSeekApi = _DeepSeekApi(AiType.DEEPSEEK.value[1])

    @staticmethod
    def get(ai_type: AiType) -> AiApi:
        if ai_type == AiType.DEEPSEEK:
            return AiApiFactory.deep_seek_api
        else:
            raise ValueError(f"Unsupported API type: {ai_type}")


if __name__ == "__main__":
    deep_seek = AiApiFactory.get(AiType.DEEPSEEK)
    content = deep_seek.query('使用大模型能力构造一个流程形成Agent，让这个Agent可以像国际象棋大师一样思考。', think=False)
    print(content)
