import collections,json,re
from common import PRIVATE
rows=json.loads((PRIVATE/'candidate-ddl-failures.private.json').read_text(encoding='utf-8'))
types=collections.Counter();features={}
for row in rows:
 for line in row['sql'].splitlines():
  match=re.match(r'^  `[^`]+` ([a-z]+)',line)
  if match:types.update([match[1]])
  for key,pattern in [('generated',r'GENERATED ALWAYS'),('check',r'\bCHECK\b'),('index',r'^  (?:UNIQUE )?KEY.*USING'),('other_option',r'ROW_FORMAT=')]:
   if re.search(pattern,line):features.setdefault(key,[]).append(line)
print('types',dict(types))
for key,lines in features.items():
 print(key,len(lines))
 for line in list(dict.fromkeys(lines))[:20]:print(line)
exprs=features['check']+features['generated']
masked=[re.sub(r"'(?:[^'\\]|'')*'",'STRING',line) for line in exprs]
print('expressionWords',dict(collections.Counter(w.lower() for line in masked for w in re.findall(r'(?<![A-Za-z0-9_`])([A-Za-z_]+)\s*\(',line))))
for line in features['check'][20:]:
 if any(k in line for k in ('json_','length','trim','like','regexp')):print(line)
failures=json.loads((PRIVATE/'candidate-ddl-failures.private.json').read_text(encoding='utf-8'))
for row in failures:
 if 'TRIGGER' in row['sql'] and any(k in row['sql'] for k in ('signature_generation_insert','system_users_signature_identity_insert','trg_dcc_reg_cert_master_immutable_bu')):print('TRIGGER:',row['sql'])
for row in failures:
 if 'CREATE TABLE' in row['sql']:
  print('TABLE:',row['sql'])
