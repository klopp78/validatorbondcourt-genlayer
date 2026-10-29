# ValidatorBondCourt for GenLayer

ValidatorBondCourt is a payable, consensus-governed service bond primitive for AI validators and their clients. A provider locks GEN against explicit service terms; the named client may open a staked dispute with evidence; GenLayer validators independently read the terms and both evidence sources before deciding the escrow distribution.

## Lifecycle

1. `create_service_bond` locks a positive GEN bond for a named client, canonical service scope, terms URL and expiry. A caller nonce produces a deterministic, replay-resistant ID.
2. `open_dispute` can only be called by that named client before expiry and requires a positive challenge stake, preventing arbitrary URLs from occupying a case path.
3. `resolve_dispute` runs a non-deterministic consensus assessment. Validators compare the decision, reason, canonical service and each immutable source hash.
4. `settle_dispute` transfers the real locked bond and stake after an approved resolution. `release_expired_bond` safely returns an undisputed bond after expiry.

The contract deliberately governs its own GEN service-bond escrow. It does not claim to slash GenLayer's native validator stake.

## Verification

Run `npm test`. Deploy `contracts/validator_bond_court.py` in Studio, create a small bond, submit a dispute with two public evidence pages and inspect the finalized bond/dispute records.
