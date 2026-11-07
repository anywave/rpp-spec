"""Static inventory of the 49 historical verdict guard mutations.

The exact-formula guard makes the native-bounds omission equivalent. Removing
orientation completeness still rejects incomplete evidence via a non-assertion
failure. Both cases stay explicit exclusions, not assertion kills. The final
two-row affinity fixture distinguishes the bindings and kills their alias.
This module only describes cases; the runner owns isolation and execution.
"""


def guard_cases() -> tuple[dict, ...]:
    """Return deterministic relative source operations and bounded test selectors."""
    M = "tools/prove_out/verdict.py"
    S = "tools/prove_out/sector_verdict.py"
    MT = "tools/prove_out/tests/test_verdict.py::"
    ST = "tools/prove_out/tests/test_sector_verdict.py::"
    cases = []

    def add(name, source, function, before, after, targets, expected="killed"):
        cases.append({
            "name": name,
            "source": source,
            "function": function,
            "before": before,
            "after": after,
            "targets": (targets,) if isinstance(targets, str) else tuple(targets),
            "expected": expected,
        })

    prod = MT + 'test_production_python_contract_reports_complete_domains_and_separate_sentinel_caveats'
    add('omit_entropy_probe', M, 'python_checks', 'for e in range(101):', 'for e in range(100):', prod)
    add('omit_completion_probe', M, 'python_checks', 'for c in range(101):', 'for c in range(100):', prod)
    add('omit_reserved_probe', M, 'python_checks', 'for reserved in range(8192)', 'for reserved in range(8191)', prod)
    add('hide_theta31_caveat', M, 'python_checks', 'coherence(RPPAddress(1, 1, 0, 0.0), RPPAddress(31, 1, 0, 0.0))', '1.0', prod)
    add('hide_null_self_caveat', M, 'python_checks', 'coherence(RPPAddress(0, 1, 0, 0.0), RPPAddress(0, 1, 0, 0.0))', '1.0', prod)
    terminal = MT + 'test_terminal_affinity_row_preserves_each_binding_contract_and_exact_disagreement'
    add('drop_canonical_binding', M, 'analyze_affinity', 'names = ("consolidated", "canonical")', 'names = ("consolidated",)', terminal)
    add('hide_exact_binding_disagreement', M, 'analyze_affinity', 'binding["exact_scaled_disagreements"] += actual != score / 255', 'binding["exact_scaled_disagreements"] += 0', terminal)
    add('conflate_terminal_binding_formulas', M, 'rtl_affinity', 'if binding == "canonical":', 'if False:', terminal)
    parser = MT + 'test_affinity_parser_refuses_incomplete_duplicate_malformed_or_out_of_domain_rows'
    add('affinity_omit_domain_guard', M, 'affinity_rows', 'if set(rows) != AFF_DOMAIN:', 'if False:', [parser + '[missing]', parser + '[outside]'])
    add('affinity_omit_duplicate_guard', M, 'affinity_rows', ' or row[:4] in rows', '', parser + '[duplicate]')
    add('affinity_omit_width_guard', M, 'affinity_rows', 'len(row) != 12 or ', '', parser + '[malformed]')
    add('affinity_coerce_invalid_integer', M, 'affinity_rows', 'tuple(map(int, line.split(",")[1:]))', 'tuple(int(v) if v.lstrip("+-").isdigit() else 0 for v in line.split(",")[1:])', parser + '[unknown-value]')
    add('affinity_ignore_unknown_rows', M, 'affinity_rows', 'raise ValueError("unknown affinity output row")', 'continue', MT + 'test_affinity_parser_rejects_unknown_rows')
    contract = MT + 'test_affinity_contract_rejects_changed_native_binding_outputs'
    for name, field, parameter in [('formula', 'rtl_formula_mismatches', 'formula'), ('threshold', 'threshold_mismatches', 'threshold'), ('threshold_independence', 'threshold_score_dependence', 'score-dependence'), ('bounds', 'rtl_bounds_failures', 'bounds')]:
        old_tuple = '("rtl_formula_mismatches", "threshold_mismatches", "threshold_score_dependence", "rtl_bounds_failures")'
        fields = ['rtl_formula_mismatches', 'threshold_mismatches', 'threshold_score_dependence', 'rtl_bounds_failures']
        after = '(' + ', '.join('"' + f + '"' for f in fields if f != field) + ')'
        add('omit_native_' + name + '_guard', M, 'require_affinity', old_tuple, after, contract + '[' + parameter + ']', 'equivalent_excluded' if name == 'bounds' else 'killed')
    orientation = MT + 'test_orientation_parser_requires_complete_unique_typed_grid_and_declared_formula'
    add('orientation_omit_complete_grid', M, 'orientation', 'if set(rows) != domain:', 'if False:', orientation, 'non_assertion_excluded')
    add('orientation_omit_duplicate_guard', M, 'orientation', ' or row[:3] in rows', '', orientation)
    add('orientation_ignore_unknown_rows', M, 'orientation', 'raise ValueError("unknown orientation row")', 'continue', orientation)
    add('orientation_omit_wrap_reverse_check', M, 'orientation', 'if wrong:', 'if False:', orientation)
    partitions = ST + 'test_actual_python_partitions_cover_domains_and_ignore_other_fields'
    add('v1_theta_boundary_moved', 'rpp/address.py', 'sector_name', 'if self.theta < 64:', 'if self.theta < 63:', partitions)
    add('v2_theta10_boundary_moved', 'rpp/address_canonical.py', 'from_theta', 'if theta <= 10:', 'if theta <= 9:', partitions)
    add('sector_phi_influences_partition', 'rpp/address_canonical.py', 'sector', 'return ThetaSector.from_theta(self.theta)', 'return ThetaSector.from_theta(self.theta + int(self.phi > 1))', partitions)
    add('sector_radius_influences_partition', 'rpp/address_canonical.py', 'sector', 'return ThetaSector.from_theta(self.theta)', 'return ThetaSector.from_theta(self.theta + int(self.radius > 0))', partitions)
    add('omit_v1_irrelevance_probes', S, 'python_checks', 'for value in range(limit):', 'for value in range(limit - 1):', partitions)
    add('omit_v2_reserved_irrelevance_probe', S, 'python_checks', '("reserved", range(8192))', '("reserved", range(8191))', partitions)
    d1 = ST + 'test_d1_tools_adapter_requires_explicit_policy_and_records_all_projection_inputs'
    add('d1_policy_default_added', S, 'tools_projection', 'harmonic, policy):', 'harmonic, policy="neutral-radius"):', d1)
    add('d1_accept_unknown_policy', S, 'tools_projection', 'if policy not in {"neutral-radius", "shell-projection"}:', 'if False:', d1)
    add('d1_omit_input_domain', S, 'tools_projection', 'if any(type(value) is not int or not 0 <= value <= maximum for value, maximum in zip((shell, theta, phi, harmonic), (3, 511, 511, 255))):', 'if False:', d1)
    add('d1_neutral_radius_leaks_shell', S, 'tools_projection', '0.5 if policy == "neutral-radius" else shell / 3', 'shell / 3', d1)
    add('d1_theta_multiplier_changed', S, 'tools_projection', 'theta * 27 // 512 + 1', 'theta * 26 // 512 + 1', d1)
    add('d1_shell_projection_changed', S, 'tools_projection', 'else shell / 3', 'else shell / 4', d1)
    sector_parser = ST + 'test_parser_rejects_corrupt_or_incomplete_native_evidence'
    add('sector_omit_complete_domain', S, 'parse_rows', 'if any(set(result[kind]) != domain for kind, domain in DOMAINS.items()):', 'if False:', [sector_parser + '[missing]', sector_parser + '[outside]'])
    add('sector_omit_duplicate_guard', S, 'parse_rows', ' or key in result[kind]', '', sector_parser + '[duplicate]')
    add('sector_coerce_invalid_integer', S, 'parse_rows', 'tuple(map(int, values))', 'tuple(int(v) if v.lstrip("+-").isdigit() else 0 for v in values)', sector_parser + '[unknown]')
    add('sector_ignore_unknown_kind', S, 'parse_rows', 'raise ValueError("unknown sector row kind")', 'continue', sector_parser + '[kind]')
    add('sector_omit_output_domain', S, 'parse_rows', ' or numbers[-1] not in range(8 if kind == "MAP" else 2)', '', sector_parser + '[output]')
    checker = ST + 'test_native_checker_separates_partition_agreement_from_graph_and_sentinel_counterexamples'
    add('sector_omit_native_partition_check', S, 'require_native', 'require(not any(result[k] for k in ("ordinary_mismatches", "same_sector_mismatches", "irrelevant_field_mismatches")), "native sector partition disagreement")', 'require(True, "native sector partition disagreement")', [checker + '[consolidated]', checker + '[canonical]'])
    add('sector_hide_sentinel_counterexamples', S, 'characterize', 'sum(rows["MAP"][t,] != ThetaSector.from_theta(t).value for t in (0, 28, 29, 30, 31))', '0', [checker + '[consolidated]', checker + '[canonical]'])
    add('sector_hide_graph_counterexamples', S, 'characterize', 'sum(flag != graph[key] for key, flag in rows["ADJ"].items())', '0', checker + '[consolidated]')
    add('sector_omit_characterized_graph_check', S, 'require_native', 'require(all(flag == (graph[key] or binding == "consolidated" and key in EXTRA_EDGES) for key, flag in rows["ADJ"].items()), "characterized RTL graph changed")', 'require(True, "characterized RTL graph changed")', ST + 'test_graph_characterization_detects_an_edge_change_without_promoting_python_equality')
    add('sector_csv_platform_crlf', S, 'csv_bytes', 'lineterminator="\\n"', 'lineterminator="\\r\\n"', ST + 'test_sector_csv_serialization_has_stable_rows_and_explicit_lf_bytes')
    decoder_summary = ST + 'test_decoder_checks_full_words_validity_and_keeps_reserved_labels_outside_ordinary_claim'
    add('decoder_conflate_sentinel_labels', S, 'decoder_check', '(ordinary_index(theta) if 1 <= theta <= 27 else 0 if theta == 0 else 7)', 'address.sector.value', decoder_summary)
    add('decoder_phi_extraction_shifted', S, 'decoder_check', 'address.phi - 1', 'address.phi', decoder_summary)
    decoder = ST + 'test_decoder_refuses_incomplete_duplicate_unknown_or_wrong_word_evidence'
    add('decoder_omit_complete_grid', S, 'parse_decoder', 'if set(rows) != {(t, p) for t in range(32) for p in range(8)}:', 'if False:', decoder + '[missing]')
    add('decoder_omit_duplicate_guard', S, 'parse_decoder', ' or row[:2] in rows', '', decoder + '[duplicate]')
    add('decoder_coerce_unknown_integer', S, 'parse_decoder', 'tuple(map(int, values))', 'tuple(int(v) if v.lstrip("+-").isdigit() else 0 for v in values)', decoder + '[unknown]')
    add('decoder_omit_component_guard', S, 'decoder_check', 'not (ordinary or components or validity)', 'not (ordinary or validity)', decoder + '[component]')
    return tuple(cases)
