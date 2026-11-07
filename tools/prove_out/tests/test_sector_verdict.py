"""Finite sector witnesses; native runs and mutations are executed by run_sector."""
import pytest

from rpp.address_canonical import RPPAddress, adjacent_sectors
from tools.prove_out import sector_verdict as sector


def complete_text(binding="consolidated"):
    """Synthetic parser control only, never independent hardware evidence."""
    lines = []
    for kind, domain in sector.DOMAINS.items():
        for key in sorted(domain):
            if kind == "MAP":
                value = sector.ordinary_index(key[0]) if 1 <= key[0] <= 27 else 0
            elif kind == "SAME":
                value = int(sector.ordinary_index(key[0]) == sector.ordinary_index(key[1]))
            elif kind == "ADJ":
                a, b = (RPPAddress(sum(sector.RANGES[index]) // 2, 1, 0, 0.0) for index in key)
                value = int(adjacent_sectors(a, b) or binding == "consolidated" and key in sector.EXTRA_EDGES)
            else:
                value = int(key[0] == 0)
            lines.append(",".join(map(str, (kind, *key, value))))
    return "\n".join(lines) + "\n"


def test_actual_python_partitions_cover_domains_and_ignore_other_fields():
    """Failing mutations: move v1 boundary64, move canonical theta10, or let phi/radius choose sector."""
    result, rows = sector.python_checks()
    assert len(rows) == 539
    assert result["v1_bins"] == dict.fromkeys(sector.V1, 64)
    assert list(result["v2_bins"].values()) == [3, 3, 4, 3, 4, 3, 4, 3]
    assert result["irrelevant_field_probes"] == {"v1": 395264, "v2": 228393}


def test_d1_tools_adapter_requires_explicit_policy_and_records_all_projection_inputs():
    """Failing mutations: add a default policy, permit unknown names, leak shell into neutral radius, or change multiplier27."""
    with pytest.raises(TypeError):
        sector.tools_projection(0, 0, 0, 0)
    for policy in ("", "default", "unknown"):
        with pytest.raises(ValueError):
            sector.tools_projection(0, 0, 0, 0, policy)
    for inputs in ((4, 0, 0, 0), (0, 512, 0, 0), (0, 0, -1, 0), (0, 0, 0, 256)):
        with pytest.raises(ValueError):
            sector.tools_projection(*inputs, "neutral-radius")
    rows = sector.d1_checks()
    assert len(rows) == 2056
    for driver in ("theta", "phi"):
        assert {r[1] for r in rows if r[0] == driver} == set(range(512))
    assert [r[6] for r in rows if r[0] == "shell"] == [128, 0, 128, 85, 128, 170, 128, 255]
    projected = sector.tools_projection(0, 64, 128, 64, "neutral-radius")
    assert (projected.theta, projected.phi, projected.omega) == (4, 2, 1)
    assert ((projected.phi - 1) * 512) // 6 == 85  # An approximate reverse, not original phi128.


@pytest.mark.parametrize("mutation", ("missing", "duplicate", "unknown", "outside", "kind", "output"))
def test_parser_rejects_corrupt_or_incomplete_native_evidence(mutation):
    """Failing mutations: drop complete-grid, duplicate, typed-integer, input-domain, row-kind or output-domain guards."""
    text = complete_text()
    first, rest = text.split("\n", 1)
    changed = {"missing": rest, "duplicate": text + first + "\n",
               "unknown": text.replace("MAP,0,0", "MAP,0,x", 1),
               "outside": text.replace("MAP,0,0", "MAP,32,0", 1),
               "kind": text + "BOGUS,0,0\n",
               "output": text.replace("MAP,0,0", "MAP,0,8", 1)}[mutation]
    with pytest.raises(ValueError):
        sector.parse_rows(changed)


@pytest.mark.parametrize("binding", ("consolidated", "canonical"))
def test_native_checker_separates_partition_agreement_from_graph_and_sentinel_counterexamples(binding):
    """Failing mutations: accept allCORE/boundary errors, hide sentinel differences, or claim adjacency equality."""
    rows = sector.parse_rows(complete_text(binding))
    sector.require_native(rows, binding)
    result, examples, _ = sector.characterize(rows)
    assert result["ordinary_mismatches"] == result["same_sector_mismatches"] == result["irrelevant_field_mismatches"] == 0
    assert result["sentinel_mismatches"] == 5 and result["adjacency_mismatches"] == (4 if binding == "consolidated" else 0)
    assert len(examples) == (9 if binding == "consolidated" else 5)
    rows["MAP"][10,] = 3
    with pytest.raises(AssertionError, match="partition"):
        sector.require_native(rows, binding)


def test_graph_characterization_detects_an_edge_change_without_promoting_python_equality():
    """Failing mutation: omit the characterized-graph check and let a changed CORE-GENE edge go unnoticed."""
    rows = sector.parse_rows(complete_text())
    rows["ADJ"][0, 1] = 0
    with pytest.raises(AssertionError, match="graph"):
        sector.require_native(rows)


def test_sector_csv_serialization_has_stable_rows_and_explicit_lf_bytes():
    """Failing mutations: change CSV order, inject a clock value, or write platform CRLF."""
    rows = (("theta", 0), ("theta", 511))
    assert sector.csv_bytes(("driver", "value"), rows) == b"driver,value\ntheta,0\ntheta,511\n"
    assert sector.csv_bytes(("driver", "value"), rows) == sector.csv_bytes(("driver", "value"), rows)


def decoder_text():
    """Synthetic protocol/parser fixture, not independently executed HDL."""
    rows = []
    for theta in range(32):
        for probe, (phi, omega, radius, reserved) in enumerate(sector.PROBES):
            label = sector.ordinary_index(theta) if 1 <= theta <= 27 else 0 if theta == 0 else 7
            rows.append(",".join(map(str, ("DEC", theta, probe, sector.decoder_word(theta, probe), label, int(1 <= theta <= 27), theta, phi, omega, radius, reserved))))
    return "\n".join(rows) + "\n"


def test_decoder_checks_full_words_validity_and_keeps_reserved_labels_outside_ordinary_claim():
    """Failing mutation: merge decoder/helper sentinel labels or ignore phi/omega/radius/reserved extraction."""
    rows = sector.parse_decoder(decoder_text())
    summary, examples = sector.decoder_check(rows)
    assert summary["encoded_inputs"] == 256 and summary["ordinary_inputs"] == 216
    assert summary["sentinel_inputs"] == summary["sentinel_label_mismatches"] == 40
    assert summary["component_mismatches"] == summary["validity_mismatches"] == 0
    assert [case["rtl"] for case in examples] == ["CORE", "SHADOW"]


@pytest.mark.parametrize("mutation", ("missing", "duplicate", "unknown", "component"))
def test_decoder_refuses_incomplete_duplicate_unknown_or_wrong_word_evidence(mutation):
    """Failing mutation: drop decoder complete-grid, duplicate, typed-value or word/component checks."""
    text = decoder_text()
    first, rest = text.split("\n", 1)
    changed = {"missing": rest, "duplicate": text + first + "\n",
               "unknown": text.replace("DEC,0,0,0,", "DEC,0,0,x,", 1),
               "component": text.replace("DEC,0,0,0,", "DEC,0,0,1,", 1)}[mutation]
    with pytest.raises((ValueError, AssertionError)):
        sector.decoder_check(sector.parse_decoder(changed))
