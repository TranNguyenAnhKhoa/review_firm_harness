import json
from pathlib import Path

root = Path(__file__).resolve().parent
b = Path(r'D:\workplace_make_firm\SrcVideo\1004.mp4').read_bytes()
offset = b.rfind(b'{"data":')
obj, _ = json.JSONDecoder().raw_decode(b[offset:].decode('utf-8', errors='replace'))
(root / 'export_metadata.json').write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(obj, ensure_ascii=False, indent=2))
