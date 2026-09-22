| Cell | accuracy_final | dup_pair_count | fragmentation_max | births_beyond_seeds | novel_absorbed | coverage_final | other_rate_final | low_confidence_share | llm_calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| anchor-cold-as-today | 0.402±0 | 0.5±1 | 4±0 | 30±0 | 75.5±0 | 0.648±0 | 0.352±0 | 0.00437±0 | 32.5±0 |
| anchor-seeded-hardened | 0.365±0.0369 | 0.333±1 | 2.67±1 | 20±0 | 76.7±7 | 0.585±0.0538 | 0.415±0.0538 | 0.0754±0 | 25±15 |
| cold-as-today | 0.0636±0.0707 | 0±0 | 4.33±3 | 30±0 | 45.3±23 | 0.473±0.163 | 0.527±0.163 | 0.0418±0 | 10.7±1 |
| cold-blind | 0.134±0.131 | 6.33±3 | 4.67±1 | 30±0 | 40.7±8 | 0.594±0.06 | 0.406±0.06 | 0.0708±0 | 13.7±6 |
| cold-hardened | 0.0861±0.0446 | 0.333±1 | 4.33±2 | 30±0 | 54±11 | 0.505±0.178 | 0.495±0.178 | 0.0622±0 | 10.3±1 |
| cold-system-placement | 0.0569±0.0723 | 0.333±1 | 4.67±1 | 30±0 | 50.7±10 | 0.486±0.0769 | 0.514±0.0769 | 0.0439±0 | 11±0 |
| dedup-cold-hardened [dedup:jaccard] | 0.0908±0.0861 | 3.33±6 | 4.33±1 | 30±0 | 52±20 | 0.495±0.168 | 0.505±0.168 | 0.066±0 | 11±3 |
| dedup-seeded-hardened [dedup:jaccard] | 0.337±0.0477 | 6.67±11 | 4±2 | 20±0 | 60±9 | 0.543±0.0846 | 0.457±0.0846 | 0.0605±0 | 15±8 |
| gatecheck-bucket | 0.397±0 | 0±0 | 3±0 | 30±0 | 81±0 | 0.643±0 | 0.357±0 | 0.0819±0 | 32±0 |
| seeded-as-today | 0.339±0.0369 | 0.667±1 | 3.67±1 | 20±0 | 58.7±18 | 0.531±0.0277 | 0.469±0.0277 | 0.0678±0 | 17.3±11 |
| seeded-blind | 0.274±0.0647 | 4.67±3 | 5±2 | 20±0 | 38±17 | 0.531±0.0416 | 0.469±0.0416 | 0.103±0 | 11.7±4 |
| seeded-hardened | 0.362±0.02 | 0±0 | 4±2 | 20±0 | 72.7±14 | 0.578±0.0308 | 0.422±0.0308 | 0.0718±0 | 18.7±15 |
| seeded-system-placement | 0.359±0.04 | 3.67±9 | 4±2 | 20±0 | 71±16 | 0.568±0.0293 | 0.432±0.0293 | 0.0747±0 | 24±10 |
| stress-imperfect-hardened | 0.244±0.135 | 2±0 | 4.33±2 | 20±0 | 55±15 | 0.572±0.165 | 0.428±0.165 | 0.0767±0 | 8.33±1 |

| Paired comparison (left − right) | Metric | Mean±range |
|---|---|---:|
| cold as-today vs blind | accuracy_final | -0.0703±0.109 |
| cold as-today vs blind | label_match_rate_of_covered | -0.0936±0.211 |
| cold as-today vs blind | coverage_final | -0.121±0.108 |
| cold as-today vs blind | other_rate_final | 0.121±0.108 |
| cold as-today vs blind | novel_absorbed | 4.67±20 |
| cold as-today vs blind | births_beyond_seeds | 0±0 |
| cold as-today vs blind | other_bucket_final | 83.3±88 |
| cold as-today vs blind | low_confidence_final | -4.33±18 |
| cold as-today vs blind | llm_calls | -3±7 |
| cold as-today vs blind | re_route_count | 152±147 |
| cold as-today vs blind | latency_p50 | 0.03±0.08 |
| cold as-today vs blind | rejected_proposals_duplicate | -7.67±16 |
| cold as-today vs blind | dup_pair_count | — |
| cold as-today vs blind | dup_pair_count_strict | — |
| cold as-today vs blind | fragmentation_max | — |
| cold as-today vs blind | n_junk | — |
| cold as-today vs blind | low_confidence_share | -0.0295±0.0719 |
| cold hardened vs blind | accuracy_final | -0.0477±0.159 |
| cold hardened vs blind | label_match_rate_of_covered | -0.0436±0.314 |
| cold hardened vs blind | coverage_final | -0.0892±0.238 |
| cold hardened vs blind | other_rate_final | 0.0892±0.238 |
| cold hardened vs blind | novel_absorbed | 13.3±13 |
| cold hardened vs blind | births_beyond_seeds | 0±0 |
| cold hardened vs blind | other_bucket_final | 56.7±163 |
| cold hardened vs blind | low_confidence_final | 1.33±9 |
| cold hardened vs blind | llm_calls | -3.33±7 |
| cold hardened vs blind | re_route_count | 112±304 |
| cold hardened vs blind | latency_p50 | -0±0.12 |
| cold hardened vs blind | rejected_proposals_duplicate | -7.67±16 |
| cold hardened vs blind | dup_pair_count | — |
| cold hardened vs blind | dup_pair_count_strict | — |
| cold hardened vs blind | fragmentation_max | — |
| cold hardened vs blind | n_junk | — |
| cold hardened vs blind | low_confidence_share | -0.00854±0.0631 |
| cold system-placement vs blind | accuracy_final | -0.077±0.142 |
| cold system-placement vs blind | label_match_rate_of_covered | -0.109±0.228 |
| cold system-placement vs blind | coverage_final | -0.108±0.0939 |
| cold system-placement vs blind | other_rate_final | 0.108±0.0939 |
| cold system-placement vs blind | novel_absorbed | 10±11 |
| cold system-placement vs blind | births_beyond_seeds | 0±0 |
| cold system-placement vs blind | other_bucket_final | 74.3±75 |
| cold system-placement vs blind | low_confidence_final | -4±22 |
| cold system-placement vs blind | llm_calls | -2.67±6 |
| cold system-placement vs blind | re_route_count | 126±129 |
| cold system-placement vs blind | latency_p50 | 0.0133±0.05 |
| cold system-placement vs blind | rejected_proposals_duplicate | -7.67±16 |
| cold system-placement vs blind | dup_pair_count | — |
| cold system-placement vs blind | dup_pair_count_strict | — |
| cold system-placement vs blind | fragmentation_max | — |
| cold system-placement vs blind | n_junk | — |
| cold system-placement vs blind | low_confidence_share | -0.0269±0.0828 |
| seeded as-today vs blind | accuracy_final | 0.0651±0.094 |
| seeded as-today vs blind | label_match_rate_of_covered | 0.121±0.176 |
| seeded as-today vs blind | coverage_final | -0.000533±0.0462 |
| seeded as-today vs blind | other_rate_final | 0.000533±0.0462 |
| seeded as-today vs blind | novel_absorbed | 20.7±1 |
| seeded as-today vs blind | births_beyond_seeds | 0±0 |
| seeded as-today vs blind | other_bucket_final | 11±42 |
| seeded as-today vs blind | low_confidence_final | -10.7±17 |
| seeded as-today vs blind | llm_calls | 5.67±8 |
| seeded as-today vs blind | re_route_count | 2±39 |
| seeded as-today vs blind | latency_p50 | 0.0533±0.01 |
| seeded as-today vs blind | rejected_proposals_duplicate | -11±10 |
| seeded as-today vs blind | dup_pair_count | — |
| seeded as-today vs blind | dup_pair_count_strict | — |
| seeded as-today vs blind | fragmentation_max | — |
| seeded as-today vs blind | n_junk | — |
| seeded as-today vs blind | low_confidence_share | -0.0349±0.0611 |
| seeded hardened vs blind | accuracy_final | 0.0882±0.0447 |
| seeded hardened vs blind | label_match_rate_of_covered | 0.109±0.0894 |
| seeded hardened vs blind | coverage_final | 0.0472±0.0216 |
| seeded hardened vs blind | other_rate_final | -0.0472±0.0216 |
| seeded hardened vs blind | novel_absorbed | 34.7±3 |
| seeded hardened vs blind | births_beyond_seeds | 0±0 |
| seeded hardened vs blind | other_bucket_final | -19±25 |
| seeded hardened vs blind | low_confidence_final | -11.7±11 |
| seeded hardened vs blind | llm_calls | 7±12 |
| seeded hardened vs blind | re_route_count | -58.7±8 |
| seeded hardened vs blind | latency_p50 | 0.457±1.28 |
| seeded hardened vs blind | rejected_proposals_duplicate | -11±10 |
| seeded hardened vs blind | dup_pair_count | — |
| seeded hardened vs blind | dup_pair_count_strict | — |
| seeded hardened vs blind | fragmentation_max | — |
| seeded hardened vs blind | n_junk | — |
| seeded hardened vs blind | low_confidence_share | -0.0312±0.0408 |
| seeded system-placement vs blind | accuracy_final | 0.0851±0.105 |
| seeded system-placement vs blind | label_match_rate_of_covered | 0.114±0.186 |
| seeded system-placement vs blind | coverage_final | 0.0364±0.0385 |
| seeded system-placement vs blind | other_rate_final | -0.0364±0.0385 |
| seeded system-placement vs blind | novel_absorbed | 33±2 |
| seeded system-placement vs blind | births_beyond_seeds | 0±0 |
| seeded system-placement vs blind | other_bucket_final | -13.3±33 |
| seeded system-placement vs blind | low_confidence_final | -10.3±9 |
| seeded system-placement vs blind | llm_calls | 12.3±7 |
| seeded system-placement vs blind | re_route_count | -47.7±40 |
| seeded system-placement vs blind | latency_p50 | 0.0267±0.01 |
| seeded system-placement vs blind | rejected_proposals_duplicate | -11±10 |
| seeded system-placement vs blind | dup_pair_count | — |
| seeded system-placement vs blind | dup_pair_count_strict | — |
| seeded system-placement vs blind | fragmentation_max | — |
| seeded system-placement vs blind | n_junk | — |
| seeded system-placement vs blind | low_confidence_share | -0.0283±0.0363 |
| seeded vs cold blind | accuracy_final | 0.14±0.179 |
| seeded vs cold blind | label_match_rate_of_covered | 0.295±0.346 |
| seeded vs cold blind | coverage_final | -0.0631±0.102 |
| seeded vs cold blind | other_rate_final | 0.0631±0.102 |
| seeded vs cold blind | novel_absorbed | -2.67±9 |
| seeded vs cold blind | births_beyond_seeds | -10±0 |
| seeded vs cold blind | other_bucket_final | 28.3±79 |
| seeded vs cold blind | low_confidence_final | 12.7±13 |
| seeded vs cold blind | llm_calls | -2±8 |
| seeded vs cold blind | re_route_count | 66.7±113 |
| seeded vs cold blind | latency_p50 | -0.0233±0.09 |
| seeded vs cold blind | rejected_proposals_duplicate | 3.33±22 |
| seeded vs cold blind | dup_pair_count | — |
| seeded vs cold blind | dup_pair_count_strict | — |
| seeded vs cold blind | fragmentation_max | — |
| seeded vs cold blind | n_junk | — |
| seeded vs cold blind | low_confidence_share | 0.0316±0.0666 |
| seeded vs cold as-today | accuracy_final | 0.275±0.0585 |
| seeded vs cold as-today | label_match_rate_of_covered | 0.509±0.103 |
| seeded vs cold as-today | coverage_final | 0.0579±0.135 |
| seeded vs cold as-today | other_rate_final | -0.0579±0.135 |
| seeded vs cold as-today | novel_absorbed | 13.3±16 |
| seeded vs cold as-today | births_beyond_seeds | -10±0 |
| seeded vs cold as-today | other_bucket_final | -44±74 |
| seeded vs cold as-today | low_confidence_final | 6.33±14 |
| seeded vs cold as-today | llm_calls | 6.67±11 |
| seeded vs cold as-today | re_route_count | -83±183 |
| seeded vs cold as-today | latency_p50 | 0±0.17 |
| seeded vs cold as-today | rejected_proposals_duplicate | 0±0 |
| seeded vs cold as-today | dup_pair_count | — |
| seeded vs cold as-today | dup_pair_count_strict | — |
| seeded vs cold as-today | fragmentation_max | — |
| seeded vs cold as-today | n_junk | — |
| seeded vs cold as-today | low_confidence_share | 0.0262±0.0365 |
| seeded vs cold hardened | accuracy_final | 0.276±0.0246 |
| seeded vs cold hardened | label_match_rate_of_covered | 0.447±0.0882 |
| seeded vs cold hardened | coverage_final | 0.0733±0.158 |
| seeded vs cold hardened | other_rate_final | -0.0733±0.158 |
| seeded vs cold hardened | novel_absorbed | 18.7±19 |
| seeded vs cold hardened | births_beyond_seeds | -10±0 |
| seeded vs cold hardened | other_bucket_final | -47.3±104 |
| seeded vs cold hardened | low_confidence_final | -0.333±9 |
| seeded vs cold hardened | llm_calls | 8.33±16 |
| seeded vs cold hardened | re_route_count | -104±196 |
| seeded vs cold hardened | latency_p50 | 0.433±1.16 |
| seeded vs cold hardened | rejected_proposals_duplicate | 0±0 |
| seeded vs cold hardened | dup_pair_count | — |
| seeded vs cold hardened | dup_pair_count_strict | — |
| seeded vs cold hardened | fragmentation_max | — |
| seeded vs cold hardened | n_junk | — |
| seeded vs cold hardened | low_confidence_share | 0.00894±0.0368 |
| seeded vs cold system-placement | accuracy_final | 0.302±0.0585 |
| seeded vs cold system-placement | label_match_rate_of_covered | 0.517±0.114 |
| seeded vs cold system-placement | coverage_final | 0.0815±0.0476 |
| seeded vs cold system-placement | other_rate_final | -0.0815±0.0476 |
| seeded vs cold system-placement | novel_absorbed | 20.3±14 |
| seeded vs cold system-placement | births_beyond_seeds | -10±0 |
| seeded vs cold system-placement | other_bucket_final | -59.3±39 |
| seeded vs cold system-placement | low_confidence_final | 6.33±8 |
| seeded vs cold system-placement | llm_calls | 13±10 |
| seeded vs cold system-placement | re_route_count | -107±65 |
| seeded vs cold system-placement | latency_p50 | -0.01±0.11 |
| seeded vs cold system-placement | rejected_proposals_duplicate | 0±0 |
| seeded vs cold system-placement | dup_pair_count | — |
| seeded vs cold system-placement | dup_pair_count_strict | — |
| seeded vs cold system-placement | fragmentation_max | — |
| seeded vs cold system-placement | n_junk | — |
| seeded vs cold system-placement | low_confidence_share | 0.0303±0.0299 |
| none vs full cold as-today | accuracy_final | — |
| none vs full cold as-today | label_match_rate_of_covered | — |
| none vs full cold as-today | coverage_final | — |
| none vs full cold as-today | other_rate_final | — |
| none vs full cold as-today | novel_absorbed | — |
| none vs full cold as-today | births_beyond_seeds | — |
| none vs full cold as-today | other_bucket_final | — |
| none vs full cold as-today | low_confidence_final | — |
| none vs full cold as-today | llm_calls | — |
| none vs full cold as-today | re_route_count | — |
| none vs full cold as-today | latency_p50 | — |
| none vs full cold as-today | rejected_proposals_duplicate | — |
| none vs full cold as-today | dup_pair_count | — |
| none vs full cold as-today | dup_pair_count_strict | — |
| none vs full cold as-today | fragmentation_max | — |
| none vs full cold as-today | n_junk | — |
| none vs full cold as-today | low_confidence_share | — |
| none vs full seeded hardened | accuracy_final | -0.00307±0.0431 |
| none vs full seeded hardened | label_match_rate_of_covered | 0.00247±0.0906 |
| none vs full seeded hardened | coverage_final | -0.00667±0.0723 |
| none vs full seeded hardened | other_rate_final | 0.00667±0.0723 |
| none vs full seeded hardened | novel_absorbed | -4±21 |
| none vs full seeded hardened | births_beyond_seeds | 0±0 |
| none vs full seeded hardened | other_bucket_final | 5±59 |
| none vs full seeded hardened | low_confidence_final | -0.667±17 |
| none vs full seeded hardened | llm_calls | -6.33±7 |
| none vs full seeded hardened | re_route_count | 5.33±91 |
| none vs full seeded hardened | latency_p50 | 0.283±1.3 |
| none vs full seeded hardened | rejected_proposals_duplicate | 0±0 |
| none vs full seeded hardened | dup_pair_count | — |
| none vs full seeded hardened | dup_pair_count_strict | — |
| none vs full seeded hardened | fragmentation_max | — |
| none vs full seeded hardened | n_junk | — |
| none vs full seeded hardened | low_confidence_share | -0.00498±0.0757 |
| dedup seeded hardened vs base | accuracy_final | -0.0246±0.04 |
| dedup seeded hardened vs base | label_match_rate_of_covered | -0.0041±0.0275 |
| dedup seeded hardened vs base | coverage_final | -0.0359±0.0754 |
| dedup seeded hardened vs base | other_rate_final | 0.0359±0.0754 |
| dedup seeded hardened vs base | novel_absorbed | -12.7±5 |
| dedup seeded hardened vs base | births_beyond_seeds | 0±0 |
| dedup seeded hardened vs base | other_bucket_final | 25±42 |
| dedup seeded hardened vs base | low_confidence_final | -1.67±9 |
| dedup seeded hardened vs base | llm_calls | -3.67±9 |
| dedup seeded hardened vs base | re_route_count | 39±107 |
| dedup seeded hardened vs base | latency_p50 | 0.0267±2.65 |
| dedup seeded hardened vs base | rejected_proposals_duplicate | 1±3 |
| dedup seeded hardened vs base | dup_pair_count | — |
| dedup seeded hardened vs base | dup_pair_count_strict | — |
| dedup seeded hardened vs base | fragmentation_max | — |
| dedup seeded hardened vs base | n_junk | — |
| dedup seeded hardened vs base | low_confidence_share | -0.0115±0.022 |
| dedup cold hardened vs base | accuracy_final | 0.00463±0.0676 |
| dedup cold hardened vs base | label_match_rate_of_covered | 0.00303±0.0355 |
| dedup cold hardened vs base | coverage_final | -0.0102±0.226 |
| dedup cold hardened vs base | other_rate_final | 0.0102±0.226 |
| dedup cold hardened vs base | novel_absorbed | -2±30 |
| dedup cold hardened vs base | births_beyond_seeds | 0±0 |
| dedup cold hardened vs base | other_bucket_final | 5±131 |
| dedup cold hardened vs base | low_confidence_final | 1.67±16 |
| dedup cold hardened vs base | llm_calls | 0.667±2 |
| dedup cold hardened vs base | re_route_count | 12.7±290 |
| dedup cold hardened vs base | latency_p50 | 17.3±26.1 |
| dedup cold hardened vs base | rejected_proposals_duplicate | 1.67±5 |
| dedup cold hardened vs base | dup_pair_count | — |
| dedup cold hardened vs base | dup_pair_count_strict | — |
| dedup cold hardened vs base | fragmentation_max | — |
| dedup cold hardened vs base | n_junk | — |
| dedup cold hardened vs base | low_confidence_share | 0.0011±0.0275 |

| Noise floor | Metric | Absolute mean±range |
|---|---|---:|
| repeats | accuracy_final | 0.0108±0 |
| repeats | label_match_rate_of_covered | 0.0432±0 |
| repeats | coverage_final | 0.0277±0 |
| repeats | other_rate_final | 0.0277±0 |
| repeats | novel_absorbed | 5±0 |
| repeats | births_beyond_seeds | 0±0 |
| repeats | other_bucket_final | 20±0 |
| repeats | low_confidence_final | 2±0 |
| repeats | llm_calls | 3±0 |
| repeats | re_route_count | 40±0 |
| repeats | latency_p50 | 0.12±0 |
| repeats | rejected_proposals_duplicate | 0±0 |
| repeats | dup_pair_count | — |
| repeats | dup_pair_count_strict | — |
| repeats | fragmentation_max | — |
| repeats | n_junk | — |
