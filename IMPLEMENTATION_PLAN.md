# Remaining delivery implementation plan

Starting point: application integration PR #4, based on protected main `b92016e`. Implementation is performed on `platform/application-acceptance`; independent review remains required before merge/promotion.

1. Deliver a frozen legacy schema baseline and a versioned PostgreSQL retrieval migration. Preserve documents, backfill vectors from saved JSON, generate search text, add indexes and package migrations in the runtime image. Use migration-owned PostgreSQL schemas; keep lightweight SQLite development initialization.
2. Test fresh databases, populated legacy upgrades, repeated upgrade, malformed/incompatible vectors, native retrieval without fallback, semantic cache and persistence after restart. Use randomly named disposable databases and never mutate production for these tests.
3. Verify the agreed demonstration application flows: ingestion/errors/authentication, graph, copilot/streaming/citations, maintenance, compliance, failure analysis and administration. Cover meaningful failures, rate limits and production authentication. Document hashing/deterministic provider limitations; paid/external providers and asynchronous ingestion remain separately scoped.
4. Strengthen deployment ordering, migration checks and release evidence. Validate the candidate on an isolated runtime stack, with the production container and current platform security gates. Keep production data and configuration protected.
5. Update operational/handoff documentation and PR #4, run required GitHub checks and leave a concrete independent-review step. After approval, promote through Jenkins, back up/migrate, match exact source/image/digest, and run deployed acceptance. Do not bypass branch protection or impersonate a reviewer.

Current implementation status is recorded in `IMPLEMENTATION_RESULTS.md` when checks finish. Teammate-specific login confirmation cannot be performed on their behalf.
