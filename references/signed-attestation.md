# Signed attestation and trust-anchor contract

MotionLoom's next trust boundary uses a **DSSE-compatible envelope** around a MotionLoom-specific JSON statement. The envelope authenticates the exact serialized predicate; it does not grant review approval. This separation follows the attestation model in SLSA [1] and the DSSE pre-authentication encoding rules [2].

## Contract boundary

| Layer | Responsibility | Must not claim |
|---|---|---|
| MotionLoom statement | Bind task, scene, source, manifest, Motion IR, runtime evidence, telemetry and provenance hashes | User approval |
| DSSE-compatible envelope | Bind payload type, exact serialized body and signer signature | Artifact quality |
| Trust policy | Select accepted algorithm, key, validity window and revocation state | Runtime correctness |
| External verifier | Report integrity, binding and signer trust with stable exit codes | Approval or PR authorization |
| Review lifecycle | Record user decision on the exact candidate | Cryptographic identity without verification |

## Canonicalization rules

The payload type is `application/vnd.motionloom.attestation+json;version=1`. The signed body is the exact UTF-8 serialized statement bytes. The DSSE pre-authentication encoding is computed over the UTF-8 payload type and those exact body bytes. A verifier must not verify one serialization and then parse a different serialization for application decisions.

The statement uses a MotionLoom-specific subject/predicate shape. `subject[*].digest.sha256` identifies the attested artifact. The predicate binds `task_id`, `scene`, context hash, source/manifest/Motion IR hashes, runtime evidence hashes and provenance chain hash. The field `approval` is present only as the constant `false` in the bundle contract so cryptographic evidence cannot be mistaken for review approval.

## Trust and key lifecycle

Trust is configured out-of-band in `trust-policy.schema.json`. A `key_id` is only a lookup hint; the verifier must still resolve the key from the configured trust policy, require `status: active`, check the validity interval, enforce the algorithm and reject revoked or unknown signers. Rotation may overlap keys, but an expired or revoked signer must not be accepted merely because its signature is mathematically valid.

The initial implementation is deliberately local-policy based and deterministic. It supports test trust anchors and explicit revocation fixtures. Production deployments may replace the trust source, but must preserve fail-closed verification and the review-first approval boundary.

## References

[1]: https://slsa.dev/spec/v1.2/attestation-model "SLSA v1.2 Software attestations"

[2]: https://github.com/secure-systems-lab/dsse/blob/master/protocol.md "DSSE Protocol v1.0.2"
