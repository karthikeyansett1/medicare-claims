"""Allowlisted public bundle: provider/aggregate data only, never credentials."""
import json,sys,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dashboard.data import load_data
ROOT=Path(__file__).resolve().parents[1]
def build(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 allowed={'README.md','index.html','app.js','style.css','data.json','measure_definitions.md'}
 if any(p.name not in allowed or not p.is_file() for p in out.iterdir()):
  raise ValueError('Output directory contains files outside the public allowlist')
 frames,manifest=load_data()
 data={k:json.loads(v.to_json(orient='records')) for k,v in frames.items()}
 data['manifest']=manifest;data['demo']=json.loads((ROOT/'deployment/demo_results.json').read_text())
 (out/'data.json').write_text(json.dumps(data,separators=(',',':')))
 for name in ['index.html','app.js','style.css','README.md']:shutil.copyfile(ROOT/'deployment/static'/name,out/name)
 shutil.copyfile(ROOT/'assistant/measure_definitions.md',out/'measure_definitions.md')
 print('Public bundle:',len(list(out.iterdir())),'allowlisted files')
if __name__=='__main__': build(sys.argv[1])
