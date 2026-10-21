"""Probe orchestration refuses missing or failed observations; packet proof is live-only."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'host'))
import service_network_probe as probe

class NetworkProbeTests(unittest.TestCase):
    def setUp(self):
        values=json.loads((ROOT/'contracts/v1/fixtures.json').read_text())['valid']
        runtime=values['runtime'];preview=probe.activation.contract.render(values['release'],runtime)
        self.target=SimpleNamespace(runtime=runtime,preview=preview,identity={'release':'exact'},protect=Mock(),unchanged=Mock())
        self.policy={'installation_id':runtime['installation_id'],'network':preview['network_policy']}
        issuer=runtime['access']['issuer'].removeprefix('https://')
        self.rows={
            'app':{key:True for key in ('modeling_route','database_verified_tls','metadata_denied','direct_public_https_denied','tls_proxy_'+issuer,'tls_proxy_api.anthropic.com','proxy_denied_example.com_443','proxy_denied_169.254.169.254_80','proxy_denied_'+issuer+'_8443')},
            'dispatcher':{key:True for key in ('modeling_route','database_verified_tls','metadata_denied','direct_public_https_denied','proxy_denied')},
            'modeling':{key:True for key in ('metadata_denied','database_denied','app_denied','public_https_denied','proxy_denied')}}
        self.calls=[]
        contexts=[patch.object(probe.service_network_install,'require_root'),
                  patch.object(probe.activation.reconcile,'Target',return_value=self.target),
                  patch.object(probe.activation.reconcile,'protected',side_effect=lambda p:p),
                  patch.object(probe.activation.contract,'read_json',return_value=self.policy),
                  patch.object(probe.service_network_install,'verify_live',return_value={'exact':'kernel-state'}),
                  patch.object(probe.activation,'containers',return_value={k:k for k in self.rows}),
                  patch.object(probe.activation,'command',side_effect=self.command)]
        for context in contexts:context.start();self.addCleanup(context.stop)
    def command(self,args,**kw):
        self.calls.append(args)
        return json.dumps(self.rows[args[4]]).encode()
    def test_all_service_paths_required_and_no_model_launch(self):
        result=probe.verify('/binding','/network')
        self.assertEqual(result['observations'],self.rows)
        self.assertEqual(result['model_executions'],0)
        self.assertEqual(len(self.calls),3)
        for call in self.calls:self.assertEqual(call[:4],['/usr/bin/docker','--host','unix:///run/docker.sock','exec'])
    def test_each_failed_or_missing_path_refuses(self):
        for role,rows in copy.deepcopy(self.rows).items():
            for key in rows:
                for value in (False,1,None):
                    self.rows[role][key]=value
                    with self.assertRaisesRegex(probe.activation.Refused,'network_probe_path_failed'):probe.verify('/binding','/network')
                del self.rows[role][key]
                with self.assertRaisesRegex(probe.activation.Refused,'network_probe_path_failed'):probe.verify('/binding','/network')
                self.rows[role][key]=True
    def test_target_mismatch_precedes_container_execution(self):
        self.policy['installation_id']='other'
        with self.assertRaisesRegex(probe.activation.Refused,'network_probe_target_changed'):probe.verify('/binding','/network')
        self.assertEqual(self.calls,[])
    def test_network_change_during_probe_refuses(self):
        with patch.object(probe.service_network_install,'verify_live',side_effect=[{'version':1},{'version':2}]):
            with self.assertRaisesRegex(probe.activation.Refused,'network_probe_state_changed'):probe.verify('/binding','/network')
