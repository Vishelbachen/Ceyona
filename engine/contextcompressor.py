class ContextCompressor:
    """
    Reduces memory/context size for long conversations
    """

    def compress(self, messages: list, max_size: int = 12):
        if len(messages) <= max_size:
            return messages

        # keep last + important summary
        head = messages[:2]
        tail = messages[-(max_size - 2):]

        return head + [{"role": "system", "content": "..." }] + tail