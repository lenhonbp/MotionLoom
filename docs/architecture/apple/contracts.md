# Apple contract boundary

The Apple application is an inspection and human-review surface. It reads canonical MotionLoom artifacts and writes only a human review decision bound to the selected task, candidate and evidence digests. It does not duplicate Python validator policy, create provenance, grant `production_approved`, set `OPEN_PR=1`, open a pull request or publish a package.

`contracts/apple/review-launch-descriptor.schema.json` defines the minimum identity-bound information a macOS or iOS review surface may accept. A descriptor is rejected when its schema version is unsupported, it has unknown fields, identifiers are invalid, an artifact root is missing, or runtime/candidate evidence digests are absent.

`contracts/apple/review-decision.schema.json` defines a record made only after explicit human action. The only allowed decisions are `request_changes`, `reviewed_no_decision` and `approve_for_next_human_step`. None is production approval. A later policy-controlled workflow may consume a record only after independently verifying the same task, candidate and evidence identity.

The initial fixtures bind to `runtime-pilot-001`. They are decoder and identity fixtures, not an approval fixture and not a claim that the candidate is production eligible.
