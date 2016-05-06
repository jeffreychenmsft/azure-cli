import os
import unittest
import yaml
from azure.cli.utils.command_test_util import CommandTestGenerator
from command_specs import TEST_DEF, ENV_VAR

class TestCommands(unittest.TestCase):
    pass

recording_dir = os.path.join(os.path.dirname(__file__), 'recordings')

def _truncate_long_running_operation(data, lro_item):
    interactions = data['interactions']
    lro_index = interactions.index(lro_item)
    for item in interactions[(lro_index+1):]:
        method = item['request'].get('method')
        code = item['response']['status'].get('code')
        if method == 'GET' and code == 202:
            interactions.remove(item)
        elif method == 'GET' and code != 202:
            lro_item['response'] = item['response']
            interactions.remove(item)
            return

def _shorten_long_running_operations(test_name):
    ''' Speeds up playback of tests that originally required HTTP polling by replacing the initial
    request with the eventual response. '''
    yaml_path = os.path.join(recording_dir, '{}.yaml'.format(test_name))
    if not os.path.isfile(yaml_path):
        return
    with open(yaml_path, 'r+b') as f:
        data = yaml.load(f)
        for item in data['interactions']:
            method = item['request'].get('method')
            code = item['response']['status'].get('code')
            # breaking a lease produces this pattern but should NOT be modified
            lease_action = item['request']['headers'].get('x-ms-lease-action')
            lease_action = lease_action[0] if lease_action else None
            if method == 'PUT' and code == 202 and lease_action != 'break':
                _truncate_long_running_operation(data, item)
        f.seek(0)
        f.write(yaml.dump(data).encode('utf-8'))
        f.truncate()

generator = CommandTestGenerator(recording_dir, TEST_DEF, ENV_VAR)
tests = generator.generate_tests()

for test_name in tests:
    _shorten_long_running_operations(test_name)
    setattr(TestCommands, test_name, tests[test_name])

if __name__ == '__main__':
    unittest.main()