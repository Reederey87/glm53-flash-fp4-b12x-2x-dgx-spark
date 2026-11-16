# Layer receipt name correction

The first docs/46 run passed all9 pytest cases on each rank with unchanged
numerical assertions (95.37s/94.74s). Each actual pytest exit is0. The surrounding
receipt validator nevertheless exited1 because its expected names still began
`test_two_host_layer_a16_replay` after the fixture was renamed to
`test_two_host_layer_matched_replay`. Preserve the original raw XML, exit files,
failed summaries and wrapper exits. Do not rewrite them into successful receipts.

Exa MCP verified the official [pytest exit contract](https://docs.pytest.org/en/stable/reference/exit-codes.html)
and [JUnit name serialization](https://docs.pytest.org/en/stable/_modules/_pytest/junitxml.html).
The correction changes only the expected test-name prefix. Nine exact cases,
zero skipped/error/failure entries and actual pytest0 remain mandatory.
Numerical fixture, reference helper, checkpoint, graph/library and bounds are
byte-identical to docs/46. Local review checked runner names against the frozen
fixture and the target replay runner before staging. This does not propose a
kernel/library improvement or require a different serving build.

Register `layer-verified-window-20261116T180000Z` with the existing docs/46 gate
and notify/watchdog/fallback/memory protections. Repeat the full9-case fixture
on both ranks and require both wrapper and pytest actual exits0. Start only
after independently verified previous B12X restoration and fallback disarm.
The complete-target setup now depends on this corrected window's9/9 gate,
restoration and fallback receipts; it cannot use the prior wrapper failure.
