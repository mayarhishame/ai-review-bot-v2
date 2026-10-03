from collections import deque

history: deque = deque(maxlen=50)
seen_deliveries: set[str] = set()