from langchain_core.messages import AIMessageChunk
from langchain_core.runnables import RunnableGenerator

import logging
from .token_buffer import TokenBuffer
from typing import (
    AsyncIterable
)


def _maybe_unquote(s: str) -> str:
    length = len(s)
    if length > 1 and s[0] == '"' and s[length - 1] == '"':
        return s[1:length-1]
    return s


class XLeapStreamingTokenizer(RunnableGenerator):
    _buffer = TokenBuffer()
    _contribution_counter: int = 0
    _token_counter: int = 0
    _trigger_format_token: str = '##--##'
    _trigger_format_token_lf = '\n##--##'

    def __init__(self):
        # noinspection PyTypeChecker
        super().__init__(self.gen)

        self.name = 'XLeapStreamingTokenizer'

    def _extract_message_from_buffer(self, is_complete: bool) -> str | None :
        first_separator = self._trigger_format_token \
            if 0 == self._contribution_counter \
            else self._trigger_format_token_lf

        buffer = self._buffer

        start = buffer.index(first_separator)
        if -1 == start:
            return None

        message_start = start + len(first_separator)
        end = buffer.index(self._trigger_format_token_lf, message_start)

        if is_complete and -1 == end:
            end = buffer.length()

        if -1 == end:
            return None

        contribution = _maybe_unquote(buffer.substring(message_start, end).strip())
        buffer.delete(start, end)
        return contribution

    def append_token(self, token: str) -> str | None:
        self._buffer.append(token)

        return self._extract_message_from_buffer(False)

    def complete(self) -> str | None:
        return self._extract_message_from_buffer(True)

    async def gen(self, chunks: AsyncIterable[AIMessageChunk]) -> AsyncIterable[str]:
        async for chunk in chunks:
            logging.info(f"XLeapStreamingTokenizer.gen chunk={chunk.content}")
            complete = self.append_token(chunk.content)
            if complete is not None:
                yield complete
        yield self.complete()
