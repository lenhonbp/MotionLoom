# CloudKit review metadata boundary

`MotionLoomReviewSync` is intentionally **local-first**. A review is written to a local outbox before it can be uploaded. The CloudKit adapter uploads only a metadata projection after `MotionLoomContractDecoder.verify` confirms that task ID, candidate ID and both evidence digests match the review launch descriptor.

| Data class | Local outbox | Private CloudKit database | Explicitly excluded |
| --- | --- | --- | --- |
| Human review decision and annotations | Yes | Metadata projection only | No production approval field exists. |
| Task/candidate IDs and evidence hashes | Yes | Yes | No raw runtime artifact bytes. |
| Source asset, texture, `.riv`, `.lottie`, project repository or secrets | No | No | Never synchronized by this adapter. |
| GitHub/PR/npm/App Store operations | No | No | Must remain an explicit human-controlled workflow outside CloudKit. |

The default database is the user’s private CloudKit database. Before enabling a production container, the app project needs a user-owned container identifier, the iCloud capability entitlement, an App ID and an explicit privacy review. The source package does **not** supply a container identifier, entitlement, Apple team ID, signing profile or server token.

Apple describes CloudKit as a framework for storing and syncing app data through the user’s iCloud account; this design deliberately narrows that scope to review metadata and does not treat CloudKit as the source of truth for source assets or repository state.[1]

## References

[1]: https://developer.apple.com/icloud/cloudkit/ "Apple Developer — CloudKit"
