import json
from abc import ABCMeta, abstractmethod
from typing import Tuple

from lxml import html
from lxml.html import Element
from telegram import ParseMode

from .message import AMessage

try:
    import bs4
except ImportError:
    bs4 = None


def make_headers(data: dict):
    return "\n".join(
        "{}: {}".format(" ".join(k.split("_")).capitalize(), v)
        for k, v in sorted(data.items(), key=lambda k_v: k_v[0])
    )


class AFormatter(metaclass=ABCMeta):
    # Actually Telegram max length is 4096 but some chars might be needed to fix markdown syntax
    MAX_CONTENT_LEN = 4000

    def __init__(self, msg: AMessage):
        self.msg = msg

    @abstractmethod
    def format(self) -> Tuple[str, str]:
        pass

    def get(self) -> Tuple[str, str]:
        body, mode = self.format()
        return body[:self.MAX_CONTENT_LEN], mode


class PlainTextFormatter(AFormatter):
    def format(self) -> Tuple[str, str]:
        data = self.msg.to_json()
        content = data.pop('content')
        headers = make_headers(data)
        return headers + "\n" + content


class JsonFormatter(AFormatter):
    def format(self) -> Tuple[str, str]:
        data = self.msg.to_json()
        content = data.pop('content')
        headers = make_headers(data)

        if isinstance(content, str):
            content = json.loads(content)

        return (
            "{}\n"
            "```json\n"
            "{}"
            "```".format(
                headers,
                json.dumps(content, indent=4, ensure_ascii=False, default=str)
            ),
            ParseMode.MARKDOWN
        )

    def get(self):
        data, mode = super(JsonFormatter, self).get()
        if not data.endswith("```"):
            data += "...\n```"
        return data


class AHtmlFormatter(AFormatter):
    def __init__(self, msg: AMessage, tree: Element = None):
        super().__init__(msg)
        self.tree = tree or html.fromstring(self.msg.content)

    def format(self):
        if bs4 is not None:
            self.msg.content = bs4.BeautifulSoup(self.msg.content, 'html.parser').get_text()
        else:
            self.msg.content = self.tree.text_content()

        return PlainTextFormatter(self.msg).format()


class DjangoErrorPageFormatter(AHtmlFormatter):
    def format(self):
        pass


class GeneralHtmlFormatter(AHtmlFormatter):
    MAPPING = {
        "django": DjangoErrorPageFormatter,
        None: 'self'
    }

    @property
    def page_type(self):
        summary = (self.tree.xpath("/html/body/div[@id='summary']") or [None])[0]
        if summary is not None:
            return 'django'
        else:
            return None

    def get(self):
        cls = self.MAPPING[self.page_type]
        if cls == 'self':
            return super().get()
        else:
            return cls(self.msg, self.tree).get()


class GeneralFormatter(AFormatter):
    MAPPING = {
        "text/html": GeneralHtmlFormatter,
        "application/json": JsonFormatter,
        None: PlainTextFormatter
    }

    def format(self) -> Tuple[str, str]:
        content_type = self.msg.content_type
        cls = self.MAPPING.get(content_type, self.MAPPING[None])
        return cls(self.msg).get()
