import uuid


class PasteReference:
    def __init__(self, threshold: int = 240):
        self._paste_cache: dict[str, str] = {}
        self.threshold = threshold

    def should_collapse(self, text: str) -> bool:
        return len(text) > self.threshold

    def collapsed(self, text: str) -> str:
        ref_id = str(uuid.uuid4())[:8]
        if '<func_call>{"func_name":' in text and "</func_call>" in text:
            ref_id = f"[func_call_{ref_id}]"
        else:
            ref_id = f"[paste_{ref_id}]"
        self._paste_cache[ref_id] = text
        return ref_id

    def expand(self, marker_text: str) -> str | None:
        handled_text = marker_text
        replaced_ids = []
        for ref_id in self._paste_cache:
            if ref_id in handled_text:
                handled_text = handled_text.replace(ref_id, self._paste_cache[ref_id])
                replaced_ids.append(ref_id)
        for ref_id in replaced_ids:
            self._paste_cache.pop(ref_id)
        return handled_text

    def clear(self):
        self._paste_cache.clear()
