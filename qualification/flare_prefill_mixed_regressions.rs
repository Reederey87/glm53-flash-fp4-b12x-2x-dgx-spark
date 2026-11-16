// Regression oracles shared by the original-policy control and bounded candidate.
#[test]
fn late_short_arrival_does_not_wait_for_older_long_completion() {
    let mut s = interactive_engine(2, false);
    s.configure_policy(PolicyConfig::latency()).unwrap();
    let long = add(&mut s, 1, 32768, 1);
    for _ in 0..128 {
        if s.request(long).unwrap().consumed_tokens >= 16384 { break; }
        step(&mut s, 0);
    }
    assert_eq!(s.request(long).unwrap().consumed_tokens, 16384);
    let short = add(&mut s, 2, 64, 1);
    let arrival = s.now_ns;
    for _ in 0..128 {
        if s.request(short).is_err() { break; }
        step(&mut s, 0);
    }
    assert!(s.request(short).is_err());
    let long_consumed = s.request(long).map_or(32768, |r| r.consumed_tokens);
    println!("LATE_SHORT wait_ns={} long_consumed={long_consumed}", s.now_ns - arrival);
    assert!(long_consumed < 32768, "new short work waited for old long completion");
}

#[test]
fn active_decode_preserves_balanced_prefill_competition() {
    fn choices(completion: bool) -> Vec<(GraphKind, usize, usize, Vec<u32>)> {
        let mut s = interactive_engine(4, true);
        let decoders = [add(&mut s, 1, 128, 4096), add(&mut s, 2, 128, 4096)];
        ready(&mut s, &decoders);
        // Test-only same-state comparison; no production hot-reconfiguration API.
        s.policy.prefill_completion = completion;
        let prompts = [add(&mut s, 3, 32768, 1), add(&mut s, 4, 4096, 1)];
        let mut result = Vec::new();
        for _ in 0..1024 {
            if prompts.iter().all(|&h| s.request(h).is_err()) { break; }
            assert!(decoders.iter().all(|&h| s.request(h).is_ok()));
            let plan = step(&mut s, 2);
            result.push((plan.kind, plan.token_capacity, plan.batch_capacity,
                         plan.lanes.iter().map(|l| l.request.slot).collect()));
        }
        assert!(prompts.iter().all(|&h| s.request(h).is_err()));
        result
    }
    let balanced = choices(false);
    let latency = choices(true);
    let first = balanced.iter().zip(&latency).position(|(a, b)| a != b)
        .unwrap_or(balanced.len().min(latency.len()));
    assert!(balanced == latency, "active decode choices differ at {first}: {:?} vs {:?}",
            balanced.get(first), latency.get(first));
}
