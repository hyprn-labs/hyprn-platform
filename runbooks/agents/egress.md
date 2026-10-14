# Runbook: egress observation

Agent users' web traffic goes through a proxy on the agent host that logs each request with the agent it came from (EGR-01). Observation only: nothing is refused. The destinations it records become the allowlist that is enforced in Phase 7 (EGR-02, POL-02).

| Part | What it does |
|---|---|
| Squid (`agents/host/files/squid.conf`) | Listens on one port per agent (3100 + UID − 20000: Ada 3101, Codd 3102) on `127.0.0.1` and the host's address; logs `agent=<name>`, method, destination, status and bytes to `/var/log/squid/access.log`; caches nothing |
| Ops Agent (`files/ops-agent.yaml`) | Ships that log to Cloud Logging as `squid_access`, nothing else |
| Firewall (`files/egress.nft`) | Counts and logs, with the user's UID, every new connection of an agent user that does not go to this host (`hyprn-egress-direct` in the kernel log); refuses only the metadata server |
| `hyprn-egress-proxy on\|off\|status` | Switches agents onto the proxy or off it: shell and session variables, rootless Docker and its containers; restarts Claude Code sessions. OpenCode sessions follow when next started |

## Switch on

After `agents/host/apply.sh`, on the host:

```bash
sudo hyprn-egress-proxy on
sudo bash ~/hyprn-provision/tests/agents/run.sh
```

Then send Ada a message in Slack and expect an answer.

## Switch off (one command)

```bash
sudo hyprn-egress-proxy off
```

Agents go direct again, as before Phase 1b; the proxy keeps running unused.

## Read the observations

```bash
CLOUDSDK_CONFIG=$HOME/.config/gcloud-hyprn gcloud logging read 'logName="projects/hyprn-agents/logs/squid_access"' --project=hyprn-agents --freshness=1d --limit=50 --format='value(jsonPayload.message)'
```

On the host: `sudo tail -f /var/log/squid/access.log`; connections that bypass the proxy: `sudo journalctl -k --grep hyprn-egress-direct --since today`; their count: `sudo nft list chain inet hyprn_agents output`.

## Record

| Date | Step | Result |
|---|---|---|
