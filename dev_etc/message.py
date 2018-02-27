import json
from abc import ABCMeta, abstractmethod


class AMessage(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def from_server(cls, *args, **kwargs) -> 'AMessage':
        return cls(*args, **kwargs)

    @classmethod
    def from_redis(cls, message) -> 'AMessage':
        kwargs = json.loads(message.decode('utf-8'))
        return cls(**kwargs)

    def __init__(self, uri, content, content_type, status_code):
        self.uri = uri
        self.content = content
        self.content_type = content_type
        self.status_code = int(status_code)

    def to_json(self) -> dict:
        return {
            "uri": self.uri,
            "content": self.content,
            "content_type": self.content_type,
            "status_code": self.status_code,
        }


class DjangoMessage(AMessage):
    @classmethod
    def from_server(cls, request, response):
        return cls(
            uri=request.get_full_path(),
            content=response.content.decode(response.charset),
            content_type=response["Content-Type"],
            status_code=response.status_code
        )