#!/usr/bin/env python3
"""Wake service for the agent host (ADR-0002).

While the host is stopped, holds one Slack Socket Mode connection per agent
app. On a direct message or mention from an allowlisted Slack user it replies
that the agent is waking, starts the host and disconnects, so the running
agent alone receives the app's events. Its cloud identity can only get,
start and stop the host; tokens and the allowlist come from Secret Manager.

Dependencies: Python 3 standard library and Debian's python3-websocket.
"""
import base64
import json
import sys
import threading
import time
import urllib.error
import urllib.request

import websocket  # Debian package python3-websocket

CONFIG = json.load(open("/etc/hyprn-agents/wake.json", encoding="utf-8"))
MD = "http://169.254.169.254/computeMetadata/v1"
INSTANCE = (
    f"https://compute.googleapis.com/compute/v1/projects/{CONFIG['project']}"
    f"/zones/{CONFIG['zone']}/instances/{CONFIG['host']}"
)
STOPPED = {"TERMINATED", "STOPPED", "SUSPENDED"}
POLL_SECONDS = 15


def log(*parts):
    print("hyprn-wake:", *parts, file=sys.stderr, flush=True)


def http(url, method="GET", headers=None, body=None):
    request = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


_token = {"value": "", "expires": 0.0}


def gcp_token():
    if time.time() > _token["expires"] - 60:
        data = http(f"{MD}/instance/service-accounts/default/token", headers={"Metadata-Flavor": "Google"})
        _token.update(value=data["access_token"], expires=time.time() + data["expires_in"])
    return _token["value"]


def gcp(url, method="GET"):
    return http(url, method, {"Authorization": f"Bearer {gcp_token()}"}, b"" if method == "POST" else None)


def secret(name):
    url = f"https://secretmanager.googleapis.com/v1/projects/{CONFIG['project']}/secrets/{name}/versions/latest:access"
    return base64.b64decode(gcp(url)["payload"]["data"]).decode().strip()


def slack(method, token, payload=None):
    request = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=json.dumps(payload or {}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except (urllib.error.URLError, ValueError) as error:
        return {"ok": False, "error": str(error)}


class Waker:
    def __init__(self, agent, allowed):
        self.agent = agent
        self.allowed = allowed
        self.app_token = secret(f"{agent}-agent-slack-app-token")
        self.bot_token = secret(f"{agent}-agent-slack-bot-token")
        self.ws = None
        self.hold_until = 0.0

    def connect(self):
        if self.ws is not None or time.time() < self.hold_until:
            return
        opened = slack("apps.connections.open", self.app_token)
        if not opened.get("ok"):
            log(self.agent, "connection refused:", opened.get("error"))
            return
        self.ws = websocket.WebSocketApp(opened["url"], on_message=self.on_envelope,
                                         on_close=lambda *_: setattr(self, "ws", None))
        threading.Thread(target=self.ws.run_forever, kwargs={"ping_interval": 30}, daemon=True).start()
        log(self.agent, "listening while the host is stopped")

    def disconnect(self):
        if self.ws is not None:
            self.ws.close()
            self.ws = None
            log(self.agent, "disconnected; host is running")

    def on_envelope(self, ws, raw):
        try:
            envelope = json.loads(raw)
        except ValueError:
            return
        if envelope.get("envelope_id"):
            ws.send(json.dumps({"envelope_id": envelope["envelope_id"]}))
        if envelope.get("type") != "events_api":
            return
        event = envelope.get("payload", {}).get("event", {})
        is_dm = event.get("type") == "message" and event.get("channel_type") == "im" and not event.get("subtype") and not event.get("bot_id")
        if not (is_dm or event.get("type") == "app_mention") or event.get("user") not in self.allowed:
            return
        thread_ts = event.get("thread_ts") or (event.get("ts") if event.get("type") == "app_mention" else None)
        payload = {"channel": event.get("channel"), "text": ":sunrise: Waking up — I'll answer in about a minute."}
        if thread_ts:
            payload["thread_ts"] = thread_ts
        slack("chat.postMessage", self.bot_token, payload)
        try:
            gcp(f"{INSTANCE}/start", "POST")
            log(self.agent, "host start requested")
        except urllib.error.URLError as error:
            log(self.agent, "start failed:", error)
        self.hold_until = time.time() + 180
        self.disconnect()


def main():
    allowed = set(json.loads(secret("agents-slack-allowed-users")))
    wakers = [Waker(agent, allowed) for agent in CONFIG["agents"]]
    while True:
        try:
            status = gcp(INSTANCE).get("status", "")
        except (urllib.error.URLError, KeyError, ValueError) as error:
            log("status check failed:", error)
            status = ""
        for waker in wakers:
            if status in STOPPED:
                waker.connect()
            elif status:
                waker.disconnect()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
