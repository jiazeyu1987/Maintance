"""Explicit owner source admission without changing a physical target's identity."""
import re


def need(condition, code):
    if not condition:
        raise ValueError(code)


def reference(value):
    return type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}', value)


def admit_target_source(configuration, request):
    targets = configuration['targets']
    target_ref, source_ref = request['targetConfigRef'], request['sourceConfigRef']
    need(target_ref in targets, 'TARGET_SOURCE_MISMATCH')
    target = targets[target_ref]
    admitted = [target['sourceConfigRef']]
    if 'targetSourceAdmissions' in configuration:
        value = configuration['targetSourceAdmissions']
        code = 'TARGET_SOURCE_ADMISSION_INVALID'
        need(type(value) is dict and set(value) == {'schemaVersion','targets'} and
             value['schemaVersion'] == 'RegisteredTargetSourceAdmissions/v1' and
             type(value['targets']) is dict and 1 <= len(value['targets']) <= 128, code)
        sources = configuration.get('sources')
        need(type(sources) is dict, code)
        for ref, refs in value['targets'].items():
            need(reference(ref) and ref in targets and type(refs) is list and
                 1 <= len(refs) <= 32 and all(reference(item) and item in sources for item in refs) and
                 len(set(refs)) == len(refs), code)
            instance = targets[ref]
            need(type(instance) is dict and instance.get('sourceConfigRef') in refs and
                 type(instance.get('mainApplication')) is dict and
                 instance['mainApplication'].get('schemaVersion') in
                     ('RegisteredMainApplication/v1','RegisteredMainApplication/v2') and
                 type(instance.get('replacement')) is dict and
                 instance['replacement'].get('schemaVersion') == 'RegisteredApplicationReplacement/v2', code)
        if target_ref in value['targets']:
            admitted = value['targets'][target_ref]
    need(source_ref in admitted, 'TARGET_SOURCE_MISMATCH')
    return target
