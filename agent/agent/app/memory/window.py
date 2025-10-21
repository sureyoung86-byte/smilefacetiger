from collections import deque

class WindowMemory:
    """维护最近k轮对话的短期记忆"""
    def __init__(self, k=6):
        self.buffer = deque(maxlen=k)

    def add(self, role, content):
        self.buffer.append({"role": role, "content": content})

    def get(self):
        return list(self.buffer)
