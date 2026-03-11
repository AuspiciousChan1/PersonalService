import enum
from typing import Any, cast

from openai import OpenAI
from PersonalService.app_params import (
    DEEPSEEK_API_BASE_URL,
    DEEPSEEK_API_KEY,
    DEEPSEEK_CHAT_MODEL,
    DEEPSEEK_REASONER_MODEL,
)

class AiType(enum.Enum):
    DEEPSEEK = 0, DEEPSEEK_API_KEY


class AiApi(object):
    def query(self, query: str, system_prompt="You are a helpful assistant", think: bool = True) -> str:
        pass


class _DeepSeekApi(AiApi):
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = DEEPSEEK_API_BASE_URL
        self.client: OpenAI = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url)

    def query(self, query: str, system_prompt="You are a helpful assistant", think: bool = True) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]
        create_completion = self.client.chat.completions.create()
        # noinspection PyTypeChecker
        response = create_completion(
            messages=messages,
            model=DEEPSEEK_REASONER_MODEL if think else DEEPSEEK_CHAT_MODEL,
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
