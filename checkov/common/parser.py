import json
import logging
import os
from os import path

import hcl2
import pycfmodel
import yaml
from cfn_tools import load_yaml, dump_yaml

import cfn_flip


class Parser():
    logger = logging.getLogger(__name__)

    def parse(self, directory, tf_definitions={}, parsing_errors={}, cf_definitions={}):
        modules_scan = []

        for file in os.listdir(directory):
            if file.endswith(".json") or file.endswith(".yml") or file.endswith(".yaml"):
                self.parse_cloudformation(cf_definitions, directory, file)
            if file.endswith(".tf"):
                self.parse_terraform(directory, file, modules_scan, parsing_errors, tf_definitions)
        for m in modules_scan:
            if path.exists(m):
                self.parse(directory=m, tf_definitions=tf_definitions, cf_definitions=cf_definitions)

    def parse_terraform(self, directory, file, modules_scan, parsing_errors, tf_definitions):
        tf_file = os.path.join(directory, file)
        if tf_file not in tf_definitions.keys():
            try:
                with(open(tf_file, 'r')) as f:
                    f.seek(0)
                    dict = hcl2.load(f)
                    tf_defenition = dict
                    tf_definitions[tf_file] = tf_defenition
                    # TODO move from here
                    # tf_defenitions = context_registry.enrich_context(tf_file,tf_defenitions)

                    for modules in dict.get("module", []):
                        for module in modules.values():
                            relative_path = module['source'][0]
                            abs_path = os.path.join(directory, relative_path)
                            modules_scan.append(abs_path)
            except Exception as e:
                self.logger.debug('failed while parsing file %s' % tf_file, exc_info=e)
                parsing_errors[tf_file] = e

    def parse_cloudformation(self, cf_definitions, directory, file):
        cf_file = os.path.join(directory, file)
        if cf_file not in cf_definitions.keys():
            with(open(cf_file, 'r')) as f:
                data = json.loads(cfn_flip.to_json(f.read()))
                if 'Resources' in data:
                    if 'Conditions' in data:
                        if data['Conditions'] == {}:
                            data.pop('Conditions')
                    resolved_data = pycfmodel.parse(data).resolve()
                    cf_definitions[cf_file] = resolved_data.Resources
