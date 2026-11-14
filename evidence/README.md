# Evidence (all owners)

No mission acceptance evidence exists yet. Store each real run under a new
`evidence/<run_id>/`: manifest.json, command/environment, commit, schema version,
input checksums, seeds, observed results, failures and logs. Never overwrite a run
or delete failures selectively. Record scaffold tests separately from acceptance.

Replay packages need manifest.json, snapshot.json, timeline.jsonl and public
terrain assets. Label simulation and REPLAY; exclude evaluator reference/secrets.
