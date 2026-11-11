"""Read an explicit current installation through its exact completed proof protocol."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import main_program_installation_selection as contract
import main_program_spug_publication as publication
import main_program_spug_publication_verify_only as legacy
import main_program_spug_control_generation_acceptance as acceptance

OLD_SCHEMAS = (legacy.INPUT_SCHEMA, 'MainProgramSpugPublicationVerificationInputs/v2')
SUMMARY_SCHEMA = 'MainProgramCurrentInstallationSummary/v1'


def need(value, code):
    if not value:
        raise ValueError('CURRENT_INSTALLATION_' + code)


class BoundDocuments:
    """Projection may read only exact pins already admitted by a formal loader."""
    def __init__(self, task, pins):
        self.task = Path(task).resolve(strict=True)
        self.pins = {}
        for pin in pins:
            need(type(pin) is dict and set(pin) == {'path','bytes','sha256'} and
                 type(pin['path']) is str and type(pin['bytes']) is int and pin['bytes'] >= 0 and
                 contract.sha(pin['sha256']), 'BOUND_PIN_INVALID')
            path = Path(pin['path'])
            need(path.is_absolute(), 'BOUND_PATH_INVALID')
            key = str(path)
            need(key not in self.pins or self.pins[key] == pin, 'BOUND_PIN_CONFLICT')
            self.pins[key] = pin

    def path_pin(self, path):
        pin = self.pins.get(str(Path(path)))
        need(pin is not None, 'UNBOUND_INPUT')
        return pin

    def read(self, reference):
        need(type(reference) is dict, 'REFERENCE_INVALID')
        if set(reference) == {'file','bytes','sha256'}:
            path = self.task / contract.local_name(reference['file'])
            expected = dict(path=str(path), bytes=reference['bytes'], sha256=reference['sha256'])
        else:
            need(set(reference) == {'path','bytes','sha256'}, 'REFERENCE_INVALID')
            path = Path(reference['path']); expected = reference
        pin = self.path_pin(path)
        need(pin == expected, 'REFERENCE_CHANGED')
        raw = publication.verify_bytes(pin)
        need(len(raw) <= 16*1024*1024, 'DOCUMENT_LIMIT')
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=contract.document)
        need(type(value) is dict, 'DOCUMENT_OBJECT_REQUIRED')
        return value

    def finish(self):
        for pin in self.pins.values():
            publication.verify_bytes(pin)
        return list(self.pins.values())


def _historical_inputs(reader, inputs):
    if inputs['schemaVersion'] == acceptance.INPUT_SCHEMA:
        custody = reader.read(inputs['historicalReadCustodyPin'])
        return reader.read(custody['verificationInputsPin'])
    return inputs


def resource_build_reference(reader, inputs):
    if inputs['schemaVersion'] == acceptance.INPUT_SCHEMA:
        custody = reader.read(inputs['historicalReadCustodyPin'])
        wrapper = reader.read(custody['resourceTransitionReferencePin'])
        transition = reader.read(wrapper['transitionCorePin'])
        transition_inputs = reader.read(transition['transitionInputsPin'])
        reference = transition_inputs['resourceBuildPin']
        need(transition['resourceBuildPin'] == reference, 'RESOURCE_BUILD_CHANGED')
        return reference
    if inputs['schemaVersion'] == OLD_SCHEMAS[1]:
        transition = reader.read(inputs['resourceTransitionPin'])
        if transition['schemaVersion'] == 'MainProgramSpugResourceTransitionReaderCustody/v1':
            transition = reader.read(transition['transitionCorePin'])
        return transition['resourceBuildPin']
    need(inputs['schemaVersion'] == OLD_SCHEMAS[0], 'INPUT_SCHEMA')
    c1 = reader.read(inputs['continuationInputsPin'])
    return c1['spugResourceBuildPin']


def published_configuration_pins(reader, inputs):
    original = _historical_inputs(reader, inputs)
    if original['schemaVersion'] == OLD_SCHEMAS[1]:
        original = reader.read(original['baseVerificationInputsPin'])
    need(original['schemaVersion'] == OLD_SCHEMAS[0], 'HISTORICAL_INPUT_SCHEMA')
    c1 = reader.read(original['continuationInputsPin'])
    generation = reader.read(c1['controlGenerationPin'])
    plan = reader.read(generation['planPin'])
    secret = reader.read(plan['privatePlanPin'])
    values = [(path, secret[name+'Settings']) for name,path in publication.SETTINGS.items()]
    need(len(secret['newConnections']) == 4, 'PUBLISHED_CONNECTION_COUNT')
    for name,value in secret['newConnections'].items():
        contract.local_name(name)
        values.append(('/run/intruoyi-spug/'+name,value))
    return [dict(path=path, bytes=len(publication.canonical(value)),
                 sha256=hashlib.sha256(publication.canonical(value)).hexdigest()) for path,value in values]


def project_runtime(reader, private, selected, inputs, kind):
    core = reader.read(selected['spugInstallationPin'])
    if kind == 'CONTROL_GENERATION_ACCEPTANCE':
        need(core.get('schemaVersion') == acceptance.SCHEMA and core.get('recordType') == 'result' and
             core.get('status') == 'PASS' and core['acceptanceInputsPin'] == selected['verificationInputsPin'] and
             core['controlGenerationPin'] == selected['controlGenerationPin'] and
             core['sourceCommit'] == selected['sourceCommit'] and
             inputs['outputFile'] == selected['spugInstallationPin']['file'], 'ACCEPTANCE_BINDING_CHANGED')
        rich = reader.read(core['privateEvidencePin'])
    else:
        need(kind == 'PUBLICATION_VERIFICATION', 'PROJECTION_KIND')
        rich = reader.read(reader.path_pin(Path(private)/(Path(selected['spugInstallationPin']['file']).stem+'.private.json')))
    rows = rich['stages']
    need([row['stage'] for row in rows] == legacy.schedule(), 'GUARD_STAGE_SET')
    reference = rows[-1]['resultPin']
    stage = reader.read(reference)
    need(stage['stage'] == 'spug-guard-after', 'GUARD_STAGE_CHANGED')
    if kind == 'CONTROL_GENERATION_ACCEPTANCE':
        need(stage['schemaVersion'] == acceptance.SCHEMA and stage['recordType'] == 'stage' and
             stage['validationError'] is None, 'GUARD_STAGE_INVALID')
    guard = stage['result']
    published = published_configuration_pins(reader, inputs)
    need(sorted(guard['configurationPins'], key=lambda row:row['path']) ==
         sorted(published, key=lambda row:row['path']), 'PUBLISHED_CONFIGURATION_CHANGED')
    resource_pin = resource_build_reference(reader, inputs)
    resource = reader.read(resource_pin)
    need(resource['status'] == 'PASS' and re.fullmatch('[0-9a-f]{40}',resource['sourceCommit']), 'RESOURCE_BUILD_INVALID')
    return dict(kind=kind, resourceBuildPin=resource_pin, resourceBuild=resource,
                guardStagePin=reference, guard=guard, publishedConfigurationPins=published)


def standard_package_pin(build, private):
    """Resolve the registered build output and optional explicit variant pin."""
    command = build.get('buildCommand')
    need(type(command) is list and all(type(s) is str for s in command) and
         command.count('--output-directory') == 1, 'PACKAGE_OUTPUT_REQUIRED')
    index = command.index('--output-directory')
    need(index+1 < len(command), 'PACKAGE_OUTPUT_REQUIRED')
    directory = Path(command[index+1]); private = Path(private).resolve(strict=True)
    need(directory.is_absolute() and directory.resolve(strict=True) == directory and
         directory.is_relative_to(private) and directory != private, 'PACKAGE_OUTPUT_INVALID')
    pin = publication.file_pin(directory/'backup-restore-standard.tgz')
    need(pin['bytes'] <= 64*1024*1024 and pin['sha256'] == build['packageSha256'], 'PACKAGE_CHANGED')
    if 'variants' in build:
        row = build['variants']['standard']
        need(row['packagePin'] == pin and row['fileCount'] == build['fileCount'] and
             row['fileManifestSha256'] == build['fileManifestSha256'], 'PACKAGE_VARIANT_CHANGED')
    return pin


def load_current_installation(task, private, *, selection_file, historical_source_custody_pin=None):
    records = contract.Records(task)
    selected = records.read(selection_file)
    need(set(selected) == {'schemaVersion','sourceCommit','controlGenerationPin','spugInstallationPin','verificationInputsPin'} and
         selected['schemaVersion'] == 'TaskMainProgramInstallations/v4' and
         type(selected['sourceCommit']) is str and re.fullmatch('[0-9a-f]{40}', selected['sourceCommit']), 'SELECTION_INVALID')
    inputs = records.pinned(selected['verificationInputsPin'])
    schema = inputs.get('schemaVersion')
    source_roles = None
    if historical_source_custody_pin is not None:
        need(schema == acceptance.INPUT_SCHEMA, 'SOURCE_CUSTODY_SCOPE')
        source_roles = acceptance.history.load_source_roles(records.task, Path(private), historical_source_custody_pin)
        need(source_roles.value['selectionPin'] == records.references[selection_file], 'SOURCE_CUSTODY_SELECTION_CHANGED')
    if schema in OLD_SCHEMAS:
        verified = legacy.validate_publication_v4(records, Path(private), selected)
        kind = 'PUBLICATION_VERIFICATION'
    elif schema == acceptance.INPUT_SCHEMA:
        if source_roles is None:
            verified = acceptance.load_completed_acceptance(records.task, Path(private), selected['spugInstallationPin'])
        else:
            verified = acceptance.load_completed_acceptance(records.task, Path(private), selected['spugInstallationPin'],
                source_roles=source_roles)
        kind = 'CONTROL_GENERATION_ACCEPTANCE'
    else:
        raise ValueError('CURRENT_INSTALLATION_INPUT_SCHEMA')
    bundle = verified['generation']
    need(bundle['generationPin'] == selected['controlGenerationPin'] and
         bundle['generation']['sourceCommit'] == selected['sourceCommit'], 'GENERATION_CHANGED')
    reader = BoundDocuments(records.task, verified['inputPins']+records.path_pins()+[publication.file_pin(Path(__file__).resolve())])
    runtime = project_runtime(reader, private, selected, inputs, kind)
    if source_roles is not None:source_roles.finish()
    return dict(selectionPin=records.references[selection_file], selection=selected, generation=bundle,
                inputPins=reader.finish(), spugRuntime=runtime)


def public_summary(current):
    selected = current['selection']; bundle = current['generation']
    build = bundle['build']
    need(build['status'] == 'PASS' and build['targetCommit'] == selected['sourceCommit'] and
         type(build['fileCount']) is int and build['fileCount'] == 147, 'MAIN_BUILD_CHANGED')
    return dict(schemaVersion=SUMMARY_SCHEMA, status='PASS', selectionPin=current['selectionPin'],
        sourceCommit=selected['sourceCommit'], controlGenerationPin=selected['controlGenerationPin'],
        spugInstallationPin=selected['spugInstallationPin'], buildPin=bundle['generation']['buildPin'],
        build={key:build[key] for key in ('fileCount','fileManifestSha256','packageSha256')},
        resourceBuildPin=current['spugRuntime']['resourceBuildPin'],
        spugCommit=current['spugRuntime']['resourceBuild']['sourceCommit'], inputPins=current['inputPins'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', required=True)
    parser.add_argument('--historical-source-custody')
    parser.add_argument('--public-summary', required=True, action='store_true')
    args = parser.parse_args()
    try:
        source_args = {}
        if args.historical_source_custody:
            source_args['historical_source_custody_pin'] = publication.file_pin(Path(args.historical_source_custody))
        result = load_current_installation(publication.TASK, publication.PRIVATE, selection_file=args.selection, **source_args)
        print(json.dumps(public_summary(result), ensure_ascii=False))
    except Exception:
        # Fail closed without leaking private source values through tracebacks.
        print('CURRENT_INSTALLATION_VALIDATION_FAILED', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
