# tests/agents

Isolation checks for the agent fleet: `hyprn-agents` principals hold no role outside the project; agent users cannot reach the metadata server, other agents' homes or Docker; skip-all-permissions mode is refused; unknown Slack senders and approvals are rejected; agent Apps cannot merge or push to `main`; no production credentials on the host.
