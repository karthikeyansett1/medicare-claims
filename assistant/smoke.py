"""Explicit opt-in billable smoke: python -m assistant.smoke."""
import json
from assistant.sql_agent import Agent, AssistantError

if __name__=='__main__':
    try:
        result=Agent().ask('Which 5 providers had the highest readmission rate in 2009 under cost-based attribution in sample 1?')
        print(json.dumps(result,default=str,indent=2))
    except AssistantError as error:
        print(str(error))
        raise SystemExit(1)
