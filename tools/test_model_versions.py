"""Run historical behavioural tests in legacy mode and native v6 tests separately."""
from pathlib import Path
import subprocess,sys,os
ROOT=Path(__file__).resolve().parents[1]
for version,folder in [('legacy','Tests'),('v6','TestsV6')]:
 print(f'=== {version}: {folder} ===',flush=True)
 env=dict(os.environ,PRISM_MODEL_VERSION=version,PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
 subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',folder],cwd=ROOT,env=env,check=True)
