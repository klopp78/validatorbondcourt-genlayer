# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

"""ValidatorBondCourt: consensus settlement for a bonded AI-validator service."""

from genlayer import *
import hashlib
import json


@gl.evm.contract_interface
class _Account:
    class View:
        pass

    class Write:
        pass


class ValidatorBondCourt(gl.Contract):
    """A fee-aware bond escrow for an AI validator's promised service terms."""

    bonds: TreeMap[str, str]
    disputes: TreeMap[str, str]
    bond_ids: DynArray[str]
    bond_count: u64

    def __init__(self):
        self.bond_count = u64(0)

    @gl.public.view
    def get_bond(self, bond_id: str) -> str:
        return self.bonds.get(bond_id.strip(), "")

    @gl.public.view
    def get_dispute(self, dispute_id: str) -> str:
        return self.disputes.get(dispute_id.strip(), "")

    @gl.public.view
    def list_bond_ids(self, offset: u64, limit: u64) -> str:
        start, count = int(offset), int(limit)
        if start < 0 or count < 1 or count > 50:
            raise Exception("invalid_page")
        return _json([self.bond_ids[i] for i in range(start, min(start + count, len(self.bond_ids)))])

    @gl.public.write.payable
    def create_service_bond(self, client: str, service_scope: str, terms_url: str, expires_at: u64, creation_nonce: str) -> str:
        if gl.message.value == u256(0):
            raise Exception("positive_bond_required")
        now, expiry = _now(), int(expires_at)
        if now <= 0 or expiry <= now or expiry > now + 2_592_000:
            raise Exception("invalid_expiry")
        provider = str(gl.message.sender_address).lower()
        client_address = str(Address(client)).lower()
        scope = _clean(service_scope, 180, "service_scope_required")
        terms = _url(terms_url, "invalid_terms_url")
        nonce = _hash(creation_nonce, "invalid_creation_nonce")
        canonical = {"client": client_address, "provider": provider, "schema": "validator-bond-court.v1", "service_scope": scope, "terms_url": terms}
        bond_id = "vbc_" + _parts([_json(canonical), str(gl.message.value), str(expiry), nonce])[:20]
        if self.bonds.get(bond_id, ""):
            raise Exception("creation_nonce_already_used")
        self.bond_count = u64(int(self.bond_count) + 1)
        bond = {"bond_id": bond_id, "canonical_service": canonical, "client": client_address, "provider": provider, "bond_gen_wei": str(gl.message.value), "expires_at": expiry, "status": "active", "dispute_id": "", "created_at": now}
        self.bonds[bond_id] = _json(bond)
        self.bond_ids.append(bond_id)
        return bond_id

    @gl.public.write.payable
    def open_dispute(self, bond_id: str, allegation_scope: str, client_evidence_url: str) -> str:
        bond = _load(self.bonds, bond_id, "unknown_bond")
        if str(gl.message.sender_address).lower() != bond["client"]:
            raise Exception("only_named_client_can_challenge")
        if bond["status"] != "active" or _now() <= 0 or _now() >= int(bond["expires_at"]):
            raise Exception("bond_not_challengeable")
        if gl.message.value == u256(0):
            raise Exception("positive_challenge_stake_required")
        allegation = _clean(allegation_scope, 180, "allegation_required")
        evidence = _url(client_evidence_url, "invalid_evidence_url")
        dispute_id = "vbd_" + _parts([bond["bond_id"], allegation, evidence, str(gl.message.value)])[:20]
        if self.disputes.get(dispute_id, ""):
            raise Exception("duplicate_dispute")
        dispute = {"dispute_id": dispute_id, "bond_id": bond["bond_id"], "client": bond["client"], "provider": bond["provider"], "allegation_scope": allegation, "client_evidence_url": evidence, "challenge_stake_wei": str(gl.message.value), "status": "open", "decision": "", "opened_at": _now(), "resolution_deadline": _now() + 172800}
        bond["status"], bond["dispute_id"] = "disputed", dispute_id
        self.disputes[dispute_id], self.bonds[bond["bond_id"]] = _json(dispute), _json(bond)
        return dispute_id

    @gl.public.write
    def resolve_dispute(self, dispute_id: str, provider_evidence_url: str) -> None:
        dispute = _load(self.disputes, dispute_id, "unknown_dispute")
        bond = _load(self.bonds, dispute["bond_id"], "unknown_bond")
        if dispute["status"] != "open" or _now() <= 0 or _now() > int(dispute["resolution_deadline"]):
            raise Exception("dispute_not_resolvable")
        provider_evidence = _url(provider_evidence_url, "invalid_provider_evidence")
        context = {"canonical_service": bond["canonical_service"], "allegation_scope": dispute["allegation_scope"], "client_evidence_url": dispute["client_evidence_url"], "provider_evidence_url": provider_evidence, "bond_id": bond["bond_id"], "bond_gen_wei": bond["bond_gen_wei"], "challenge_stake_wei": dispute["challenge_stake_wei"]}

        def leader_fn():
            return _json(_assess(context))

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                proposed = _assessment(leader_result.calldata)
                independent = _assessment(_json(_assess(context)))
            except Exception:
                return False
            return all(proposed[key] == independent[key] for key in ["decision", "reason", "terms_hash", "client_evidence_hash", "provider_evidence_hash", "bundle_hash", "canonical_service"])

        assessment = _assessment(gl.vm.run_nondet_unsafe(leader_fn, validator_fn))
        dispute.update({"status": "resolved", "decision": assessment["decision"], "provider_evidence_url": provider_evidence, "assessment": assessment, "resolved_at": _now()})
        bond["status"] = "resolved"
        self.disputes[dispute_id], self.bonds[bond["bond_id"]] = _json(dispute), _json(bond)

    @gl.public.write
    def settle_dispute(self, dispute_id: str) -> None:
        dispute = _load(self.disputes, dispute_id, "unknown_dispute")
        bond = _load(self.bonds, dispute["bond_id"], "unknown_bond")
        if dispute["status"] != "resolved" or bond["status"] != "resolved":
            raise Exception("dispute_not_resolved")
        bond_value, stake_value = u256(int(bond["bond_gen_wei"])), u256(int(dispute["challenge_stake_wei"]))
        if dispute["decision"] == "client_upheld":
            _Account(Address(bond["client"])).emit_transfer(value=bond_value + stake_value)
        elif dispute["decision"] == "provider_upheld":
            _Account(Address(bond["provider"])).emit_transfer(value=bond_value + stake_value)
        else:
            _Account(Address(bond["provider"])).emit_transfer(value=bond_value)
            _Account(Address(bond["client"])).emit_transfer(value=stake_value)
        dispute["status"], bond["status"] = "settled", "settled"
        self.disputes[dispute_id], self.bonds[bond["bond_id"]] = _json(dispute), _json(bond)

    @gl.public.write
    def release_expired_bond(self, bond_id: str) -> None:
        bond = _load(self.bonds, bond_id, "unknown_bond")
        if bond["status"] != "active" or _now() <= int(bond["expires_at"]):
            raise Exception("bond_not_expired")
        _Account(Address(bond["provider"])).emit_transfer(value=u256(int(bond["bond_gen_wei"])))
        bond["status"] = "expired_released"
        self.bonds[bond["bond_id"]] = _json(bond)


def _assess(context: dict) -> dict:
    terms, client, provider = _render(context["canonical_service"]["terms_url"]), _render(context["client_evidence_url"]), _render(context["provider_evidence_url"])
    hashes = {"terms_hash": terms["hash"], "client_evidence_hash": client["hash"], "provider_evidence_hash": provider["hash"]}
    bundle = _hash(_json({"service": context["canonical_service"], "allegation": context["allegation_scope"], **hashes}), "invalid_bundle")
    if not terms["readable"] or not client["readable"] or not provider["readable"]:
        return {"decision": "inconclusive", "reason": "source_unavailable", "bundle_hash": bundle, "canonical_service": context["canonical_service"], **hashes}
    prompt = """You are a strict GenLayer bonded-service dispute judge. Use only the rendered terms and evidence. Return minified JSON only: decision (client_upheld|provider_upheld|inconclusive) and reason (terms_breached|terms_satisfied|insufficient_evidence)."""
    data = {"service": context["canonical_service"], "allegation": context["allegation_scope"], "terms": terms["content"], "client_evidence": client["content"], "provider_evidence": provider["content"]}
    raw = json.loads(gl.nondet.exec_prompt(prompt + "\n" + _json(data)))
    decision, reason = str(raw.get("decision", "inconclusive")).lower(), str(raw.get("reason", "insufficient_evidence")).lower()
    if decision not in ("client_upheld", "provider_upheld", "inconclusive") or reason not in ("terms_breached", "terms_satisfied", "insufficient_evidence"):
        decision, reason = "inconclusive", "insufficient_evidence"
    if (decision == "client_upheld" and reason != "terms_breached") or (decision == "provider_upheld" and reason != "terms_satisfied"):
        decision, reason = "inconclusive", "insufficient_evidence"
    return {"decision": decision, "reason": reason, "bundle_hash": bundle, "canonical_service": context["canonical_service"], **hashes}


def _assessment(raw: str) -> dict:
    data = json.loads(raw)
    if data.get("decision") not in ("client_upheld", "provider_upheld", "inconclusive"):
        raise Exception("invalid_assessment")
    for key in ("reason", "terms_hash", "client_evidence_hash", "provider_evidence_hash", "bundle_hash", "canonical_service"):
        if key not in data:
            raise Exception("missing_assessment_field")
    return data


def _render(url: str) -> dict:
    try:
        content = " ".join(str(gl.nondet.web.render(url, mode="text")).split())
        return {"readable": len(content) >= 80, "content": content[:12000], "hash": hashlib.sha256(content.encode()).hexdigest()}
    except Exception:
        return {"readable": False, "content": "", "hash": hashlib.sha256(b"SOURCE_UNAVAILABLE").hexdigest()}


def _load(store, key: str, error: str) -> dict:
    raw = store.get(key.strip(), "")
    if not raw:
        raise Exception(error)
    return json.loads(raw)


def _now() -> int:
    try:
        return int(gl.message.block_timestamp)
    except Exception:
        return 0


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _hash(value: str, error: str) -> str:
    candidate = value.strip().lower()
    if len(candidate) != 64 or any(ch not in "0123456789abcdef" for ch in candidate):
        raise Exception(error)
    return candidate


def _parts(values: list) -> str:
    return hashlib.sha256("".join(str(len(str(v))) + ":" + str(v) for v in values).encode()).hexdigest()


def _clean(value: str, limit: int, error: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned or len(cleaned) > limit:
        raise Exception(error)
    return cleaned


def _url(value: str, error: str) -> str:
    url = value.strip()
    if not url.startswith("https://") or len(url) > 500:
        raise Exception(error)
    return url
