import re
import uuid


class PasteReference:
    def __init__(self, threshold: int = 120):
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

    def expand(self, marker_text: str) -> str:
        """只展开 marker_text 中实际存在的引用"""
        handled_text = marker_text
        # 找出 marker_text 中的引用标记(完整匹配)
        ref_pattern = r"\[(func_call|paste)_([a-f0-9]{8})\]"
        matches = re.findall(ref_pattern, marker_text)

        for ref_type, ref_id in matches:
            full_ref = f"[{ref_type}_{ref_id}]"
            if full_ref in self._paste_cache:
                handled_text = handled_text.replace(full_ref, self._paste_cache[full_ref])
                del self._paste_cache[full_ref]

        return handled_text

    def clear(self):
        self._paste_cache.clear()
