# ValidatorBondCourt for GenLayer

ValidatorBondCourt is a payable, consensus-governed service bond primitive for AI validators and their clients. A provider locks GEN against explicit service terms; the named client may open a staked dispute with evidence; GenLayer validators independently read the terms and both evidence sources before deciding the escrow distribution.

## Lifecycle

1. `create_service_bond` locks a positive GEN bond for a named client, canonical service scope, terms URL, immutable terms snapshot and expiry. The contract SHA-256 commits the normalized snapshot at creation, so later URL changes cannot alter settlement terms. A caller nonce produces a deterministic, replay-resistant ID.
2. `open_dispute` can only be called by that named client before expiry and requires a positive challenge stake, preventing arbitrary URLs from occupying a case path.
3. `resolve_dispute` can only be called by the recorded provider, which prevents a third party from supplying provider evidence. Validators compare the decision, reason, immutable service snapshot and each evidence hash.
4. `settle_dispute` transfers the real locked bond and stake after an approved resolution. If nobody resolves an open dispute before its deadline, `recover_expired_dispute` returns the provider bond and client stake separately; neither deposit can remain locked indefinitely. `release_expired_bond` safely returns an undisputed bond after expiry.

The contract deliberately governs its own GEN service-bond escrow. It does not claim to slash GenLayer's native validator stake.

## Verification

Run `npm test`. Deploy `contracts/validator_bond_court.py` in Studio, create a small bond, submit a dispute with two public evidence pages and inspect the finalized bond/dispute records.

## Studionet deployment

The submitted source is deployed at [`0xa3C52F40C515B59F35f6afa20e74De070B5dB013`](https://explorer-studio.genlayer.com/address/0xa3C52F40C515B59F35f6afa20e74De070B5dB013). The deployed ABI exposes `create_service_bond`, `open_dispute`, `resolve_dispute`, `settle_dispute`, and `recover_expired_dispute`.
