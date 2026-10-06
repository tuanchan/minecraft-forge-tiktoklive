import copy
import json
import tempfile
import unittest
from unittest.mock import patch
from test_settings import isolated_settings, web, bridge
import missions
from reward_options import options_for, reward_payload


def rule():
    return dict(id='diamonds', title='Đào kim cương', kind='diamond', mob='*', enabled=True,
                target=100, milestones=10, death_penalty=10, death_mode='percent', mode='2d', x=50, y=15, scale=1, reset=0)


class MissionTests(unittest.TestCase):
    def test_persistence_and_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            before=missions.load(directory)
            next_config={'enabled':True,'rules':[rule()]}
            saved=missions.save(directory,{'base':before,'config':next_config})['config']
            self.assertEqual(missions.load(directory),saved)
            self.assertEqual(saved['rules'][0]['title'],'Đào kim cương')
            with self.assertRaises(ValueError):
                missions.save(directory,{'base':before,'config':next_config})
            self.assertFalse(missions.snapshot(directory)['online'])
            legacy=rule();legacy.pop('milestones')
            self.assertEqual(missions.validate({'enabled':True,'rules':[legacy]})['rules'][0]['milestones'],10)

    def test_validation(self):
        for field,value in [('target',0),('target',1.5),('milestones',0),('milestones',101),('death_penalty',101),('x',float('nan')),
                            ('scale',0),('kind','unsupported'),('mode','4d'),('mob','../bad'),('enabled',1)]:
            row=rule();row[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):missions.validate({'enabled':True,'rules':[row]})
        with self.assertRaises(ValueError):missions.validate({'enabled':True,'rules':[rule(),rule()]})

    def test_gift_save_and_combo_dispatch(self):
        gift=dict(gift_name='Rose',action='special',target='mission_penalty',amount=2,mission_id='diamonds',penalty=7)
        with isolated_settings() as gui:
            controller=web.Controller();controller.save({'gui':gui,'bridge':{'gift_actions':[gift]}})
            saved=controller.state()['bridge']['gift_actions'][0]
            self.assertEqual(json.loads(reward_payload(saved)),{'mission_id':'diamonds','penalty':7})
            with patch.object(bridge,'send_interaction') as send:
                bridge.dispatch_gift_action({},saved,'Viewer','viewer','Gift',repeat_count=3)
                self.assertEqual(send.call_count,6)
                for call in send.call_args_list:
                    self.assertEqual(call.args[1],'mission_penalty')
                    self.assertEqual(json.loads(call.kwargs['payload']),{'mission_id':'diamonds','penalty':7})
        for value in [-1,0,1.5,True,float('inf')]:
            with self.subTest(value=value),self.assertRaises(ValueError):options_for({**gift,'penalty':value})
        self.assertEqual(options_for({**gift,'mission_id':'*'})['mission_id'],'*')


if __name__=='__main__':unittest.main()
