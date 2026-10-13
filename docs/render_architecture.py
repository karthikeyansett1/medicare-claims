"""Render the documented architecture; run with .venv/bin/python docs/render_architecture.py."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent / 'img'
fig, ax = plt.subplots(figsize=(14, 8), facecolor='#f5f7fb')
ax.set(xlim=(0, 14), ylim=(0, 8))
ax.axis('off')
ax.text(.5, 7.5, 'From synthetic claims to defensible comparisons', fontsize=22, weight='bold', color='#142d4e')
ax.text(.5, 7.05, 'Samples 1 + 2  •  PostgreSQL / dbt / Python  •  Performance years 2009–2010', fontsize=12, color='#53657d')

def box(x, y, w, h, title, detail, color='#e3ecf8'):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.04,rounding_size=0.1',facecolor=color,edgecolor='#9bb0c8',lw=1))
    ax.text(x+w/2,y+h-.29,title,ha='center',va='center',fontsize=12,weight='bold',color='#142d4e')
    ax.text(x+w/2,y+h/2-.15,detail,ha='center',va='center',fontsize=10,color='#34465e',linespacing=1.5)

def arrow(start,end):
    ax.annotate('',xy=end,xytext=start,arrowprops=dict(arrowstyle='-|>',color='#617992',lw=1.6,mutation_scale=14))

for x,title,detail in [(0.5,'Source CSVs','CMS DE-SynPUF\n16 files + references'),(3.8,'Bronze','Raw TEXT + lineage\nAtomic Python COPY'),(7.1,'Silver','Typed claims + enrollment\nSegments / date audits'),(10.4,'Gold','Dimensions + detailed facts\nMember-year cost')]:
    box(x,5.2,2.8,1.2,title,detail)
for x in [3.3,6.6,9.9]: arrow((x,5.8),(x+.5,5.8))
box(7.1,3.05,6.1,1.35,'Attribution + analytical marts','A visits / B allowed  •  CCS principal diagnosis  •  Readmissions\nPython 2008 expected-cost fit → provider cost / utilization mart')
arrow((11.8,5.2),(11.8,4.4))
box(.5,3.05,5.65,1.35,'Controls across the pipeline','Source identity + SHA-256  •  dbt contracts\nIndependent reconciliation  •  Isolated Docker / GitHub CI','#edf1f5')
box(7.1,.8,2.8,1.35,'Dashboard','Aggregate/provider extracts\nFour Streamlit pages','#ddf1ec')
box(10.4,.8,2.8,1.35,'Analytics assistant','Allowlisted read-only SQL\nLive API evaluation deferred','#fff0d7')
arrow((8.5,3.05),(8.5,2.15))
arrow((11.8,3.05),(11.8,2.15))
ax.text(.5,2.15,'One semantic specification',fontsize=14,weight='bold',color='#142d4e')
ax.text(.5,1.8,'Shared measure definitions connect the analysis,\ndashboard and assistant. Synthetic results do not\nestablish real provider performance.',fontsize=11,color='#53657d',linespacing=1.5,va='top')
ax.text(.5,.25,'Conceptual data flow; the assistant can query selected gold and mart tables. CI uses a separate 1,000-member fixture.',fontsize=10,color='#53657d')
fig.savefig(OUT / 'architecture.png',dpi=180,bbox_inches='tight',facecolor=fig.get_facecolor())
fig.savefig(OUT / 'architecture.svg',bbox_inches='tight',facecolor=fig.get_facecolor())
plt.close(fig)
