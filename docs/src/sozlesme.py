"""Contract appendix helpers: canonical JSON (RFC 8785 subset), fingerprints, projections and fixture checks.

build.py imports this module to re-verify data/sozlesme-fixture.json on every build. The fixture holds only
strings, integers, booleans, null, objects and arrays; floats are rejected because JCS number formatting is not
implemented here (money travels as Decimal text, F9). For such values RFC 8785 equals sorted-key JSON with no
insignificant whitespace, UTF-8 output and JSON.stringify string escaping, which json.dumps below produces.
"""
import hashlib
import json
import re

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _check(o, path="$"):
    if isinstance(o, float):
        raise ValueError(f"float at {path}: fixtures use integers or Decimal text")
    if isinstance(o, dict):
        for k, v in o.items():
            if not isinstance(k, str) or not k.isascii():
                raise ValueError(f"non-ASCII or non-string key at {path}: {k!r}")
            _check(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            _check(v, f"{path}[{i}]")


def jcs(o):
    _check(o)
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def fp(o):
    return hashlib.sha256(jcs(o).encode("utf-8")).hexdigest()


def pick(d, keys):
    """Projection: every listed key is written; a missing key is written as null (absent and null hash alike)."""
    return {k: d.get(k) for k in keys}


# name -> (input, fields, ordering and missing-field rule); rendered as the projection table in the appendix
PROJECTION_DOC = [
    ("schema_fingerprint", "DocType metadata anlık görüntüsü (meta_snapshot)",
     "doctype, catalog_version, fields[fieldname, fieldtype, permlevel]",
     "fields fieldname'e göre sıralı; başka alan girmez"),
    ("context_manifest_fingerprint", "context.build yanıtı (ek 2)",
     "capability, capability_version, catalog_version, schema_fingerprint, selection, records[doctype, name, revision], fields, data_classes, evidence_sources[source, version]",
     "records name'e, fields ve data_classes alfabetik, evidence_sources (source, version) çiftine, selection.exclude alfabetik sıralı; fingerprint ve generated_at girmez"),
    ("params_fingerprint", "runs.start isteği (ek 3)",
     "capability, capability_version, mode, selection, context_manifest_fingerprint",
     "idempotency_key girmez; aynı projeksiyon tekrar korumasının payload parmak izidir (F6)"),
    ("quote_fingerprint", "Tedarikçi belgesinden alıntı",
     "source, version, page, quote",
     "quote belgedeki metnin birebir kendisidir; boşluk normalleştirilmez"),
    ("changeset fingerprint", "ChangeSet (ek 4)",
     "changeset_id, run_id, base, items[doctype, name, revision, status, risk, reason, changes[field, old, new, evidence]]",
     "items (doctype, name) çiftine, changes field'a göre sıralı; evidence yalnızca quote_fingerprint listesi, alfabetik; eksik alan null yazılır; confidence ve fingerprint girmez"),
    ("approval_fingerprint", "changesets.approve isteği ve onaylayan (ek 5)",
     "changeset_id, changeset_fingerprint, approved_items, excluded_items, approver, via, grant_id",
     "approved_items ve excluded_items alfabetik; idempotency_key ve zaman damgaları girmez; sunucu bu değeri ayrıca imzalar"),
]


def projections(F):
    ctx, cs = F["context"], F["changeset"]

    def schema():
        m = F["meta_snapshot"]
        return {"doctype": m["doctype"], "catalog_version": m["catalog_version"],
                "fields": sorted((pick(f, ["fieldname", "fieldtype", "permlevel"]) for f in m["fields"]),
                                 key=lambda f: f["fieldname"])}

    def selection(sel):
        s = dict(sel)
        s["exclude"] = sorted(s.get("exclude") or [])
        return pick(s, ["doctype", "filter", "exclude"])

    def context():
        p = pick(ctx, ["capability", "capability_version", "catalog_version", "schema_fingerprint"])
        p["selection"] = selection(ctx["selection"])
        p["records"] = sorted((pick(r, ["doctype", "name", "revision"]) for r in ctx["records"]), key=lambda r: r["name"])
        p["fields"] = sorted(ctx["fields"])
        p["data_classes"] = sorted(ctx["data_classes"])
        p["evidence_sources"] = sorted((pick(e, ["source", "version"]) for e in ctx["evidence_sources"]),
                                       key=lambda e: (e["source"], e["version"]))
        return p

    def params():
        r = F["start_req"]
        p = pick(r, ["capability", "capability_version", "mode", "context_manifest_fingerprint"])
        p["selection"] = selection(r["selection"])
        return p

    def quote(q):
        return pick(q, ["source", "version", "page", "quote"])

    def changeset():
        items = []
        for it in cs["items"]:
            p = pick(it, ["doctype", "name", "revision", "status", "risk", "reason"])
            p["changes"] = sorted(({"field": c["field"], "old": c.get("old"), "new": c.get("new"),
                                    "evidence": sorted(e["quote_fingerprint"] for e in c.get("evidence", []))}
                                   for c in it.get("changes", [])), key=lambda c: c["field"])
            items.append(p)
        items.sort(key=lambda i: (i["doctype"], i["name"]))
        return {"changeset_id": cs["changeset_id"], "run_id": cs["run_id"],
                "base": pick(cs["base"], ["catalog_version", "schema_fingerprint"]), "items": items}

    def approval():
        a, r = F["approve_req"], F["approve_res"]
        return {"changeset_id": a["changeset_id"], "changeset_fingerprint": a["changeset_fingerprint"],
                "approved_items": sorted(a["approved_items"]), "excluded_items": sorted(a.get("excluded_items") or []),
                "approver": r["approver"], "via": r["via"], "grant_id": r.get("grant_id")}

    return {"schema": schema, "context": context, "params": params, "quote": quote,
            "changeset": changeset, "approval": approval}


def verify(F, e5_states, error_codes):
    """Return a list of error strings; empty means the fixture is internally consistent."""
    errs = []
    P = projections(F)
    ctx, cs, sr, ar, res = F["context"], F["changeset"], F["start_req"], F["approve_req"], F["result"]

    def eq(label, got, want):
        if got != want:
            errs.append(f"fixture {label}: {got} != computed {want}")

    try:
        sch = fp(P["schema"]())
        eq("context.schema_fingerprint", ctx["schema_fingerprint"], sch)
        eq("changeset.base.schema_fingerprint", cs["base"]["schema_fingerprint"], sch)
        eq("spec.schemaFingerprint", F["spec"]["schemaFingerprint"], sch)
        eq("context.fingerprint", ctx["fingerprint"], fp(P["context"]()))
        eq("start_req.context_manifest_fingerprint", sr["context_manifest_fingerprint"], ctx["fingerprint"])
        eq("start_res.params_fingerprint", F["start_res"]["params_fingerprint"], fp(P["params"]()))
        qf = {(q["source"], q["version"], q["page"]): fp(P["quote"](q)) for q in F["alintilar"]}
        for it in cs["items"]:
            for ch in it.get("changes", []):
                for ev in ch["evidence"]:
                    key = (ev["source"], ev["version"], ev["page"])
                    if key not in qf:
                        errs.append(f"fixture: evidence {key} has no quote vector")
                    else:
                        eq(f"quote_fingerprint {key}", ev["quote_fingerprint"], qf[key])
        eq("changeset.fingerprint", cs["fingerprint"], fp(P["changeset"]()))
        eq("approve_req.changeset_fingerprint", ar["changeset_fingerprint"], cs["fingerprint"])
        eq("approve_res.approval_fingerprint", F["approve_res"]["approval_fingerprint"], fp(P["approval"]()))
    except (ValueError, KeyError, TypeError) as ex:
        errs.append(f"fixture projection failed: {ex}")

    def walk(o, path="$"):
        if isinstance(o, dict):
            for k, v in o.items():
                if ("fingerprint" in k.lower()) and not (isinstance(v, str) and HEX64.match(v)):
                    errs.append(f"fixture {path}.{k}: not a 64-digit lowercase SHA-256")
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
    walk({k: v for k, v in F.items() if k not in ("about",)})

    # identity consistency across the flow
    m = F["manifest"]
    for label, cap, ver in (("context", ctx["capability"], ctx["capability_version"]),
                            ("start_req", sr["capability"], sr["capability_version"])):
        if (cap, ver) != (m["capability"], m["version"]):
            errs.append(f"fixture {label}: capability or version differs from the manifest")
    if sr["selection"] != ctx["selection"]:
        errs.append("fixture: start selection differs from the context manifest selection")
    if set(sr["selection"].get("exclude") or []) & {r["name"] for r in ctx["records"]}:
        errs.append("fixture: an excluded record is in the context manifest")
    if sr["mode"] not in m["modes"]:
        errs.append("fixture: start mode is not allowed by the manifest")
    ctx_rev = {r["name"]: r["revision"] for r in ctx["records"]}
    cs_items = {i["name"]: i for i in cs["items"]}
    if set(ctx_rev) != set(cs_items):
        errs.append("fixture: ChangeSet items differ from the context manifest records")
    for n, it in cs_items.items():
        if it.get("revision") != ctx_rev.get(n):
            errs.append(f"fixture: {n} revision differs between context and ChangeSet")
    if cs["run_id"] != F["start_res"]["run_id"] or res["run_id"] != cs["run_id"]:
        errs.append("fixture: run ids differ")
    proposed = {n for n, i in cs_items.items() if i["status"] == "proposed"}
    ambiguous = {n for n, i in cs_items.items() if i["status"] == "ambiguous"}
    appr, excl = set(ar["approved_items"]), set(ar.get("excluded_items") or [])
    if appr & excl:
        errs.append("fixture: an item is both approved and excluded")
    if (appr | excl) != proposed:
        errs.append("fixture: every proposed item must be either approved or excluded, and nothing else")
    if ar["changeset_id"] != cs["changeset_id"]:
        errs.append("fixture: approval names another ChangeSet")
    want_dec = "approved" if not excl else "partially_approved"
    if F["approve_res"]["decision"] != want_dec:
        errs.append(f"fixture: approval decision should be {want_dec}")
    outcomes = {r["name"]: r["outcome"] for r in res["results"]}
    if set(outcomes) != set(cs_items):
        errs.append("fixture: result does not list every ChangeSet item")
    for n, o in outcomes.items():
        ok = (o in ("applied", "conflict", "failed") if n in appr else
              o == "excluded" if n in excl else o == "ambiguous" if n in ambiguous else False)
        if not ok:
            errs.append(f"fixture: outcome {o} is not allowed for {n}")
    applied = sum(1 for o in outcomes.values() if o == "applied")
    open_items = sum(1 for o in outcomes.values() if o in ("conflict", "failed", "ambiguous"))
    want = "failed" if applied == 0 else "partially_done" if open_items else "done"
    if res["status"] != want:
        errs.append(f"fixture: result status {res['status']} should be {want}")
    for r in res["results"]:
        if r.get("error") and r["error"]["code"] not in error_codes:
            errs.append(f"fixture: result error {r['error']['code']} is not in the error catalogue")

    # Run state machine against E5
    states = [s["durum"] for s in F["run_durumlari"]]
    if set(states) != set(e5_states):
        errs.append("fixture: Run states differ from E5: " + " ".join(sorted(set(states) ^ set(e5_states))))
    nxt = {s["durum"]: s["sonraki"] for s in F["run_durumlari"]}
    for s, ns in nxt.items():
        for n in ns:
            if n not in nxt:
                errs.append(f"fixture: state {s} -> unknown {n}")
    for s in ("running", "applying"):
        if "cancel_requested" not in nxt.get(s, []):
            errs.append(f"fixture: {s} must allow cancel_requested (Durdur)")
    path = F["ornek_yol"]
    for a, b in zip(path, path[1:]):
        if b not in nxt.get(a, []):
            errs.append(f"fixture: example path {a} -> {b} is not an allowed transition")
    if path[-1] != res["status"] or F["start_res"]["status"] != path[0]:
        errs.append("fixture: example path does not start at the start response and end at the result status")
    for g in F["gecersiz"]:
        if g["hata"] not in error_codes:
            errs.append(f"fixture: invalid example error {g['hata']} is not in the error catalogue")
    return errs
