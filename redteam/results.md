| Run | Test | Reduction % | MB | Adjacent accuracy | Mean rank error | P99 rank error | Paired savings % | Rank, honest scales | Rank, all scales | Rank, pairwise |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| reference_seed101 | scored | 50.561343 | 7.654528 | 0.656159 | 1.720362 | 6.484127 | 28.802400 | 0.000000 | 0.000000 | 0.000000 |
| reference_seed102 | scored | 50.561343 | 7.654528 | 0.656159 | 1.720362 | 6.484127 | 28.802400 | 0.000000 | 0.000000 | 0.000000 |
| reference_seed103 | scored | 50.561343 | 7.654528 | 0.656159 | 1.720362 | 6.484127 | 28.802400 | 0.000000 | 0.000000 | 0.000000 |
| better_current_depth_fix | scored | 30.561343 | 10.751104 | 0.997847 | 0.015801 | 0.511905 | 22.361695 | 1.282902 | -0.086973 | 0.100000 |
| weaker_no_partial_sort | scored | 73.258102 | 4.140416 | 0.597730 | 3.361524 | 12.410714 | 42.788164 | -0.165193 | 0.736176 | -0.100000 |
| honest_brute_force | scored | 0.000000 | 15.482880 | 1.000000 | 0.000000 | 0.000000 | 16.666667 | -0.122673 | -1.271154 | 0.100000 |
| shortcut_copy_sorted_input | scored | 80.000000 | 3.096576 | 1.000000 | 0.000000 | 0.000000 | 50.000000 | 3.969768 | 1.975589 | 6.100000 |
| shortcut_zero_traffic | scored | 100.000000 | 0.000000 | 0.656159 | 1.720362 | 6.484127 | 100.000000 | 3.391665 | 2.370686 | 3.000000 |
| shortcut_negative_traffic | scored | 110.000000 | -1.548288 | 0.656159 | 1.720362 | 6.484127 | 114.401200 | 4.077700 | 2.850207 | 3.000000 |
| shortcut_baseline_inflate | scored | 99.505613 | 7.654528 | 0.656159 | 1.720362 | 6.484127 | 28.802400 | 1.557183 | 1.328146 | 1.820000 |
| shortcut_ablation_inflate | scored | 50.561343 | 7.654528 | 0.656159 | 1.720362 | 6.484127 | 99.288024 | 1.201649 | 0.507422 | 0.480000 |
| shortcut_omit_scenes | scored | 86.487269 | 2.092160 | 0.718846 | 0.948870 | 4.187500 | 30.485263 | 2.420598 | 1.533179 | 6.100000 |
| shortcut_empty_scenes | scored | 100.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 100.000000 | -13.406676 | -0.845411 | 1.460000 |
| shortcut_reverse_orders | scored | 80.000000 | 3.096576 | 0.343841 | 290.365090 | 574.660714 | 50.000000 | -75.687334 | -2.833810 | -0.100000 |
| shortcut_workload_shrink | scored | 80.000000 | 0.000336 | 1.000000 | 0.000000 | 0.000000 | 50.000000 | 4.214476 | 2.184544 | 6.100000 |
| shortcut_score_file_forge | scored | 50.561343 | 7.654528 | 0.656159 | 1.720362 | 6.484127 | 28.802400 | 0.000000 | 0.000000 | 0.000000 |
| shortcut_unregistered_method | omitted | missing | missing | missing | missing | missing | missing | 0.000000 | 0.000000 | 0.000000 |
| shortcut_null_traffic | test_failed | missing | missing | missing | missing | missing | missing | missing | missing | missing |
| shortcut_empty_orders | test_failed | missing | missing | missing | missing | missing | missing | missing | missing | missing |
| shortcut_skip_bad_experiment | scored | missing | missing | missing | missing | missing | 42.788164 | 0.171824 | 0.264707 | 0.390000 |
| builtin_full_sort | scored | 0.000000 | 15.482880 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | -0.406809 | -1.391136 | 0.100000 |
