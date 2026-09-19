# Backend API Evidence

## Scope

- Handler: `RuntimeControlOperationAction.buildReleaseArguments`
- Contract: a runtime-console `build-release` request with `publishScope=with-data` must invoke the PowerShell publisher with explicit `-PublishScope with-data -ConfirmText WITH-DATA`; `code-only` continues to pass both skip switches.
- No database schema, authentication, authorization, or remote environment change is in scope.

## BDD

- `BDD: with-data runtime command preserves explicit data scope -> Given a valid build-release request with publishScope=with-data, When the runtime console builds the command preview, Then the command contains -PublishScope with-data and -ConfirmText WITH-DATA and does not contain either skip switch.`

## Required Verification

- RED: `mvn -Dtest=RuntimeControlContractTest#buildReleaseWithDataPreviewContainsNasAndRuntimeBaseArguments test -q` -> FAIL before the command-builder fix because the preview omitted both explicit scope and confirmation arguments.
- GREEN: the same targeted test and the runtime-control contract suite pass after the fix.
- Static verification: PowerShell AST and release governance contract tests remain passing.

## Risk Boundary

- No real `build-release`, NAS copy, `publish-test`, server write, database write, or MinIO write is executed.

## Verification

- RED: `mvn -Dtest=RuntimeControlContractTest#buildReleaseWithDataPreviewContainsNasAndRuntimeBaseArguments test -q` -> FAIL before the fix because the generated arguments omitted `-PublishScope with-data` and `-ConfirmText WITH-DATA`.
- GREEN: `mvn -Dtest=RuntimeControlContractTest#buildReleaseCodeOnlyPreviewSkipsDatabaseAndMinioData+buildReleaseWithDataPreviewContainsNasAndRuntimeBaseArguments test -q` -> PASS.
- Contract suite: `mvn -Dtest=RuntimeControlContractTest test -q` -> PASS.

## Observability

- The runtime action preview exposes the exact PowerShell argument list and records `publishScope` in safe parameters; no credential value is added to evidence.
