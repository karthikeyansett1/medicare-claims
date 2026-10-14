"""Build an explicit runtime allowlist; never copy the repository wholesale."""
import shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 for name in ('README.md','Dockerfile','requirements.txt'):shutil.copyfile(ROOT/'deployment/docker'/name,out/name)
 files=['dashboard/app.py','dashboard/data.py','dashboard/__init__.py','assistant/demo.py','assistant/__init__.py','assistant/semantic_layer.yaml','assistant/measure_definitions.md','deployment/demo_results.json']
 files += [str(p.relative_to(ROOT)) for p in (ROOT/'dashboard/data').iterdir() if p.suffix in ('.csv','.json')]
 for name in files:
  dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
 print('Docker demo bundle prepared; live agent deliberately requires a separate owner-controlled release.')
if __name__=='__main__':build(sys.argv[1])
