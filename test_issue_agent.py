from dotenv import load_dotenv
load_dotenv()

from state.agent_state import AgentState
from agents.issue_agent import run_issue_agent

state = AgentState(issue_url="https://github.com/psf/requests/issues/6707")
state = run_issue_agent(state)

print("Bug description:", state.bug_description)
print("Reproduction steps:", state.reproduction_steps)
print("Affected files hint:", state.affected_files_hint)
print("Status:", state.status)
print("Tokens used:", state.total_tokens_used)