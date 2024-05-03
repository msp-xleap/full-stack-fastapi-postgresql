

class TokenBuffer:
    _buffer = list[str]()
    _last_search: str | None = None
    _last_str_index: int = -1
    _last_buffer_index: int = -1

    def append(self, token: str):
        for s in token:
            self._buffer.append(s)

    def index(self, search: str, start: int = 0):
        """
            Returns the first index of the search. Returns -1 if the search value
            is not present!
        :param search:
        :param start:
        :return:
        """
        search_length = len(search)
        buff = self._buffer
        buff_length = len(buff)
        if search_length > buff_length or start > buff_length:
            return -1
        buffer_index = -1 + start
        while True:
            buffer_index += 1
            if buffer_index >= buff_length:
                return -1

            try:
                idx = self._buffer.index(search[0], buffer_index)
            except ValueError:
                return -1

            if search_length + idx > buff_length:
                return -1
            search_index = 0
            while (search_index + 1 < search_length
                   and idx + 1 + search_index < buff_length):
                search_index += 1
                if buff[idx + search_index] != search[search_index]:
                    break
            if (search_index == search_length-1
                    and buff[idx + search_index] == search[search_index]):
                return idx

    def length(self):
        return len(self._buffer)

    def substring(self, start: int, end: int) -> str:
        return "".join(self._buffer[start:end])

    def delete(self, start: int, end: int):
        del self._buffer[start:end]
