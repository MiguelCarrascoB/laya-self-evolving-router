"""LLM-based semantic audit of final router registries.

This module deliberately has no dependency on the laya package: its public
helpers are useful for tests and the command line entry point is self-contained.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


POLICY_VERSION = "q14-v1"
TEMPERATURE = 0
GROUND_TRUTH_LABELS = [
    "scheduling", "coding_help", "fitness_health", "math_homework",
    "travel_planning", "shopping", "cooking_recipes", "writing_editing",
    "data_analysis", "translation", "novel_esports_betting",
    "novel_beekeeping", "novel_board_games", "novel_genealogy_research",
    "novel_watch_collecting", "novel_astronomy", "novel_home_plants",
    "novel_car_maintenance", "novel_wine_tasting", "novel_music_theory",
]
VALID_MAPPINGS = set(GROUND_TRUTH_LABELS) | {"junk", "unclear"}

POLICY_TEXT = """You are a taxonomy auditor for a prompt router. Judge the final registry using exactly this metric policy:
- dup_pairs: two categories are DUPLICATES iff a typical user prompt could reasonably be routed to either one — same scope, interchangeable. Example: gift_selection vs purchase_advice. Each pair gets a borderline: true|false flag (borderline = arguable) and a one-line why.
- fragmentation (distinct from duplication): one ground-truth intent's traffic split across several narrower-but-distinct categories (e.g. coding_help split into programming_basics + web_layout + file_streaming). Narrower-but-distinct sub-intents are NOT dups. Fragmentation is measured as: for each ground-truth intent, the number of categories mapped to it.
- mapping: every registry category is mapped to exactly one of: one of the 20 ground-truth labels listed below, "junk" (catch-all / orphan / matches no dataset intent), or "unclear".
When mapping, a category for the same intent as novel_x maps to novel_x; the prefix is just the split marker.
"""


def build_system_prompt() -> str:
    labels = "\n".join(f"- {label}" for label in GROUND_TRUTH_LABELS)
    return POLICY_TEXT + "\nThe 20 ground-truth labels are:\n" + labels + "\n\nReturn only the requested JSON object."


def build_user_prompt(categories: list[dict[str, Any]]) -> str:
    lines = []
    for index, category in enumerate(categories, 1):
        name = category.get("name", "") if isinstance(category, dict) else ""
        description = category.get("description", "") if isinstance(category, dict) else ""
        lines.append(f"{index}. {name}: {description}")
    return (
        "Audit this registry. Return ONLY a JSON object with exactly these keys: "
        '`mapping` (list of {"name", "mapped_to", "why"}), '
        '`dup_pairs` (list of {"a", "b", "borderline", "why"}), and `notes` (string).\n\n'
        + "Registry categories:\n" + "\n".join(lines)
    )


def _normalize_categories(
    raw: list[Any], descriptions: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    """Accept the documented objects and older result files' name strings.

    Historical result files store registry categories as bare names; their
    birth descriptions are recovered from ``category_creations`` via
    ``descriptions`` so the judge can weigh scope overlap.
    """
    descriptions = descriptions or {}
    normalized = []
    for category in raw:
        if isinstance(category, str):
            normalized.append({"name": category, "description": descriptions.get(category, "")})
        elif isinstance(category, dict):
            normalized.append(category)
    return normalized


def _candidate_objects(text: str) -> list[str]:
    # Whole JSON first; these candidates handle markdown fences/preambles.
    candidates = [text.strip()]
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            _, end = decoder.raw_decode(text[match.start():])
        except (ValueError, json.JSONDecodeError):
            continue
        candidates.append(text[match.start():match.start() + end])
    return candidates


def _parse_judge_response(text: str) -> dict[str, Any]:
    """Parse and normalize a judge response, never raising for bad model text."""
    warnings: list[str] = []
    obj: Any = None
    for candidate in _candidate_objects(text or ""):
        try:
            value = json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            obj = value
            break
    if obj is None:
        return {"mapping": [], "dup_pairs": [], "notes": "", "_warnings": ["no JSON object found"]}

    mapping: list[dict[str, str]] = []
    for required_key in ("mapping", "dup_pairs", "notes"):
        if required_key not in obj:
            warnings.append(f"missing {required_key}")
    raw_mapping = obj.get("mapping", [])
    if not isinstance(raw_mapping, list):
        warnings.append("mapping was not a list")
        raw_mapping = []
    for item in raw_mapping:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("mapped_to"), str):
            warnings.append("dropped malformed mapping entry")
            continue
        name, target = item["name"].strip(), item["mapped_to"].strip()
        if not name or target not in VALID_MAPPINGS:
            warnings.append(f"dropped invalid mapping: {name!r}")
            continue
        mapping.append({"name": name, "mapped_to": target, "why": str(item.get("why", "")).strip()})

    pairs: list[dict[str, Any]] = []
    raw_pairs = obj.get("dup_pairs", [])
    if not isinstance(raw_pairs, list):
        warnings.append("dup_pairs was not a list")
        raw_pairs = []
    for item in raw_pairs:
        if not isinstance(item, dict) or not isinstance(item.get("a"), str) or not isinstance(item.get("b"), str) or not isinstance(item.get("borderline"), bool):
            warnings.append("dropped malformed duplicate pair")
            continue
        a, b = item["a"].strip(), item["b"].strip()
        if not a or not b or a == b:
            warnings.append("dropped invalid duplicate pair")
            continue
        pairs.append({"a": a, "b": b, "borderline": item["borderline"], "why": str(item.get("why", "")).strip()})
    notes = obj.get("notes", "")
    if not isinstance(notes, str):
        warnings.append("notes was not a string")
        notes = str(notes)
    result = {"mapping": mapping, "dup_pairs": pairs, "notes": notes}
    if warnings:
        result["_warnings"] = warnings
    return result


def _fragmentation(mapping: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in mapping:
        target = item.get("mapped_to") if isinstance(item, dict) else None
        if target in GROUND_TRUTH_LABELS:
            counts[target] = counts.get(target, 0) + 1
    return dict(sorted(counts.items()))


def _summary(n_categories: int, mapping: list[dict[str, Any]], dup_pairs: list[dict[str, Any]]) -> dict[str, Any]:
    fragmentation = _fragmentation(mapping)
    return {
        "n_categories": n_categories,
        "n_mapped": sum(item.get("mapped_to") in GROUND_TRUTH_LABELS for item in mapping),
        "n_junk": sum(item.get("mapped_to") == "junk" for item in mapping),
        "n_unclear": sum(item.get("mapped_to") == "unclear" for item in mapping),
        "dup_pair_count": len(dup_pairs),
        "dup_pair_count_strict": sum(not item.get("borderline", False) for item in dup_pairs),
        "fragmentation_max": max(fragmentation.values(), default=0),
        "fragmentation": fragmentation,
    }


def _judge(client: Any, model: str, categories: list[dict[str, Any]]) -> dict[str, Any]:
    messages = [{"role": "system", "content": build_system_prompt()}, {"role": "user", "content": build_user_prompt(categories)}]
    last = ""
    for attempt in range(4):
        try:
            response = client.chat.completions.create(model=model, messages=messages, temperature=TEMPERATURE, max_completion_tokens=6000)
        except Exception as exc:
            # Some OpenAI-compatible reasoning endpoints reject an explicit
            # temperature=0 and only permit their default. Preserve the
            # experiment's requested setting where supported, but remain usable.
            if "temperature" not in str(exc).lower():
                raise
            response = client.chat.completions.create(model=model, messages=messages, max_completion_tokens=6000)
        last = response.choices[0].message.content or ""
        parsed = _parse_judge_response(last)
        if parsed["mapping"] or parsed["dup_pairs"] or parsed.get("notes") or not parsed.get("_warnings"):
            return parsed
    return _parse_judge_response(last)


def _prior_key(output: dict[str, Any], path: Path) -> str | None:
    """Return the key of a prior judgment for ``path``, relative or absolute.

    Resumed judge files may have been written from another cwd or with the
    other path spelling; matching by resolved path avoids paid re-judging and
    duplicate entries. The prior key is kept as-is.
    """
    if str(path) in output:
        return str(path)
    target = path.resolve()
    for key in output:
        if key != "run_config" and Path(key).resolve() == target:
            return key
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", type=Path, help="run result JSON files to judge")
    parser.add_argument("--out", required=True, type=Path,
                        help="judge JSON to write; prior successful judgments in it are reused")
    parser.add_argument("--model", default=None, help="judge model (default: $OPENAI_MODEL or gpt-5.6-luna)")
    args = parser.parse_args(argv)
    load_dotenv()
    model = args.model or os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    from openai import OpenAI
    client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"), api_key=os.getenv("OPENAI_API_KEY", ""))
    output: dict[str, Any] = {"run_config": {"model": model, "temperature": TEMPERATURE, "timestamp": datetime.now(timezone.utc).isoformat(), "policy_version": POLICY_VERSION}}
    # Resume by default: keep prior successful judgments, re-judge failed ones.
    if args.out.exists():
        try:
            prior = json.loads(args.out.read_text())
        except (ValueError, json.JSONDecodeError):
            prior = {}
        if isinstance(prior, dict):
            for key, value in prior.items():
                if key != "run_config" and isinstance(value, dict) and value.get("judged_ok"):
                    output[key] = value
    rows = []
    for path in args.results:
        prior_key = _prior_key(output, path)
        if prior_key is not None:
            rows.append((prior_key, output[prior_key]["summary"]))
            continue
        try:
            data = json.loads(path.read_text())
        except OSError as exc:
            print(f"{path}: unreadable ({exc.strerror or exc}); skipped", file=sys.stderr)
            continue
        except (ValueError, json.JSONDecodeError):
            print(f"{path}: not valid JSON; skipped", file=sys.stderr)
            continue
        if not isinstance(data, dict):
            print(f"{path}: not a run results object; skipped", file=sys.stderr)
            continue
        registry = data.get("registry_final")
        if not isinstance(registry, dict) or not isinstance(registry.get("categories"), list):
            print(f"{path}: missing registry_final.categories; skipped", file=sys.stderr)
            continue
        created = {
            c.get("name", ""): c.get("description", "")
            for c in data.get("category_creations", [])
            if isinstance(c, dict)
        }
        categories = _normalize_categories(registry["categories"], created)
        if len(categories) != len(registry["categories"]):
            print(f"{path}: ignored malformed registry category entries", file=sys.stderr)
        judged = _judge(client, model, categories)
        judged["fragmentation"] = _fragmentation(judged["mapping"])
        judged["summary"] = _summary(len(categories), judged["mapping"], judged["dup_pairs"])
        judged_ok = bool(judged["mapping"]) and len(judged["mapping"]) == len(categories)
        if not judged_ok:
            print(
                f"{path}: judge returned an incomplete mapping "
                f"({len(judged['mapping'])}/{len(categories)}); treat results as unreliable",
                file=sys.stderr,
            )
        output[str(path)] = {
            **{k: judged[k] for k in ("mapping", "dup_pairs", "fragmentation", "summary")},
            "warnings": judged.get("_warnings", []),
            "judged_ok": judged_ok,
        }
        # Save after every file so interruptions lose nothing (resume keeps these).
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(output, indent=2) + "\n")
        s = judged["summary"]
        rows.append((str(path), s))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2) + "\n")
    print("registry | categories | dup strict/borderline | junk | fragmentation max")
    for path, s in rows:
        print(f"{path} | {s['n_categories']} | {s['dup_pair_count_strict']}/{s['dup_pair_count'] - s['dup_pair_count_strict']} | {s['n_junk']} | {s['fragmentation_max']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
