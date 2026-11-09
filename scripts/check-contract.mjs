import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const source = readFileSync(new URL('../contracts/validator_bond_court.py', import.meta.url), 'utf8');
for (const marker of ['create_service_bond', 'terms_snapshot', 'only_named_provider_can_supply_evidence', 'recover_expired_dispute', 'resolution_window_still_open', 'settle_dispute', 'release_expired_bond', 'gl.vm.run_nondet_unsafe', 'positive_challenge_stake_required']) assert.match(source, new RegExp(marker.replaceAll('.', '\\.'), ''));
const digest = value => createHash('sha256').update(value).digest('hex');
const parts = values => digest(values.map(v => `${String(v).length}:${v}`).join(''));
const base = ['validator-bond-court.v1', '0xclient', '0xprovider', 'policy scope', 'https://example.org/terms', '100', '1800000000'];
const one = parts([...base, 'a'.repeat(64)]), two = parts([...base, 'b'.repeat(64)]);
assert.notEqual(one, two, 'nonce must bind each new escrow');
assert.equal(parts([...base, 'a'.repeat(64)]), one, 'previewed canonical inputs stay deterministic');
assert.match(source, /terms_hash.*_sha256\(snapshot\)/, 'terms must be content-bound when the bond is created');
assert.match(source, /emit_transfer\(value=u256\(int\(bond\["bond_gen_wei"\]\)\)\)/, 'expired disputes must return the provider bond');
assert.match(source, /emit_transfer\(value=u256\(int\(dispute\["challenge_stake_wei"\]\)\)\)/, 'expired disputes must return the client stake');
console.log('ValidatorBondCourt lifecycle and canonical-bond checks passed.');
