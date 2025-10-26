from pathlib import Path
import json

history = json.loads(Path('/tmp/history.json').read_text(encoding='utf-8'))
science = json.loads(Path('/tmp/science.json').read_text(encoding='utf-8'))
english = json.loads(Path('/tmp/english.json').read_text(encoding='utf-8'))

base = history
base['id'] = 'history_science_english_plan'
base['title'] = '历史 科学 英语 周计划'
base['assets'].extend(science['assets'])
base['assets'].extend(english['assets'])
base['updated_at'] = history['updated_at']

output_path = Path('config/history_science_english.json')
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding='utf-8')
print('Wrote', output_path, 'with', len(base['assets']), 'assets')

