# Spug test-server configuration delivery

User requested uploading the missing runtime configuration for another computer.

Scope: export the currently selectable test-server smallapp safe/fast bindings, their test-server restore routes and required bridge credentials. Do not export IntRuoyi or other servers' runtime credentials. Do not modify running services or execute backup/restore.

Delivery uses an AES-256-GCM encrypted archive committed to Git. Its randomly generated key stays outside the repository under a current-user/SYSTEM-only Windows ACL and must travel separately. Plaintext credential-bearing configuration must never be logged or committed. The archive is a configuration snapshot, not a successful installation or runtime-readiness claim.

Verification: validate JSON, binding closure and existing source configuration schemas; decrypt and compare the complete payload; reject an incorrect key and altered ciphertext; scan staged plaintext for exported credential values; verify remote int_main after push. Do not repeat unrelated previously passed business tests.

Machine-local task IDs, SSH credentials, remote controller installations, tunnel processes, current source/target identities and target occupancy require validation on the receiving computer. No fallback or default credentials are allowed.

## Verification results

- Exported 13 files: two public state settings, one scoped bridge registry, five bridge connections, five matching authentication-header files.
- Scope closure passed: exactly safe/fast smallapp sources on `.58`, all restore and overwrite routes restricted to `.58`; no other-server or IntRuoyi credentials exported.
- Existing `smallapp_entry.settings`, `smallapp_simple.configuration` and `HttpBridge` source/target validators accepted the decrypted snapshot.
- AES-GCM decrypt round trip passed; wrong-key and altered-ciphertext authentication were rejected.
- Delivery CLI decrypted into a new ACL-restricted directory outside Git; all 13 byte counts and SHA256 values match the manifest, as do the two public JSON copies.
- Exported plaintext and ciphertext were checked against actual credential strings and the key; no plaintext credential or key was present. The key remains in the original computer's private cache directory, outside Git.
- No service configuration was changed; no tunnel, backup or restore was started. Receiving-machine installation, live identity validation and business rehearsal are still outstanding.

Status: ready_for_closeout; configuration package and instructions verified, awaiting Git push confirmation.
