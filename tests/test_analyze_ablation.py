import importlib.util
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("analyze_ablation", Path(__file__).parents[1] / "scripts/analyze_ablation.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(mod)


def run(seed, accuracy=0.5, low=2, bucket=3, repeat=0):
    return {"_parsed": {"cell": "cold-blind", "permutation_seed": seed, "repeat": repeat},
            "metrics": {"accuracy_final": accuracy, "coverage_final": .7, "other_rate_final": .3,
                         "low_confidence_final": low, "other_bucket_final": bucket,
                         "rejected_proposals": {"duplicate": 1}, "novel_absorbed": 4,
                         "births_beyond_seeds": 2},
            "meta": {"llm_calls": 3}, "latency": {"p50": 10}}


def test_filename_parsing_suffixes():
    assert mod.parse_filename("cold-hardened-fshot-none-p42.json")["permutation_seed"] == 42
    p = mod.parse_filename("dedup-cold-hardened-fshot-none-p13-dedup-token-jaccard-025-r2.json")
    assert p["dedup_tag"] == "token-jaccard-025" and p["repeat"] == 2
    assert mod.parse_filename("not-a-run.json") is None


def test_aggregate_mean_range_and_missing_keys():
    result = mod.aggregate_runs([run(13, .4), run(42, .8), {"_parsed": {"permutation_seed": 77}, "metrics": {}}])
    assert result["accuracy_final"] == {"mean": .6, "min": .4, "max": .8, "range": .4}
    assert result["llm_calls"]["mean"] == 3
    assert mod.aggregate_runs([run(1)])["accuracy_final"]["range"] == 0


def test_paired_delta_and_noise_floor():
    left = [run(13, .8), run(42, .6)]
    right = [run(13, .5), run(42, .5)]
    assert mod.paired_deltas(left, right)["accuracy_final"]["mean"] == .2
    repeats = [run(13, .4, repeat=1), run(13, .5, repeat=2)]
    assert mod.noise_floor(repeats)["accuracy_final"]["mean"] == .1


def test_gate_and_markdown():
    gate = mod.gate_decomposition([run(1, low=1, bucket=3)])
    assert gate["low_confidence_share"] == .25
    text = mod.render_markdown({"cold-blind": {"accuracy_final": {"mean": .5, "range": 0}, "low_confidence_share": {"mean": .25, "range": 0}}}, {}, None)
    assert "cold-blind" in text and "Noise floor" in text


def test_baseline_shape_is_tolerated():
    assert mod._value({"metrics": {"accuracy_final": .2}}, "accuracy_final") == .2
    assert mod._value({"metrics": {}}, "coverage_final") is None


def test_judge_summary_matches_path_aliases(tmp_path):
    run_path = tmp_path / "cold-blind-fshot-none-p13.json"
    summary = {"dup_pair_count": 2, "fragmentation_max": 4, "n_junk": 1}
    judge = {str(run_path.resolve()): {"summary": summary}}

    assert mod._judge_summary(judge, str(run_path)) == summary
    assert mod._judge_summary({run_path.name: {"summary": summary}}, run_path) == summary
