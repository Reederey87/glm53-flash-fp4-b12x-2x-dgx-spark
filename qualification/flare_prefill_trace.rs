//! Diagnostic child of the pinned scheduler's policy_tests module.
//! Uses its real selector and synthetic completion/cost fixture, never CUDA.
use super::*;

fn prefill_trace(policy_name: &str, policy: PolicyConfig, count: usize) -> Vec<u32> {
    let mut scheduler = interactive_engine(count, false);
    scheduler.configure_policy(policy).unwrap();
    let handles: Vec<_> = (1..=count as u32)
        .map(|id| add(&mut scheduler, id, 32768, 1))
        .collect();
    let mut first_output_ns = vec![None; count];
    let mut first_output_prefill_dispatch = vec![None; count];
    let mut consumed = vec![0usize; count];
    let mut prefill_slots = Vec::new();
    let mut prefix_at_first_output = None;
    let mut progressed_at_first_output = None;
    let mut dispatches = 0;
    for _ in 0..1024 {
        if handles.iter().all(|h| scheduler.request(*h).is_err()) {
            break;
        }
        let plan = scheduler.plan().expect("diagnostic workload must make progress");
        let fence = Fence(scheduler.submitted.0 + 1);
        if plan.kind == GraphKind::Prefill {
            for lane in &plan.lanes {
                let index = handles.iter().position(|h| *h == lane.request).unwrap();
                consumed[index] += lane.tokens;
                prefill_slots.push(lane.request.slot);
            }
        }
        scheduler.commit(&plan, fence).unwrap();
        let duration = plan.estimated_duration_ns();
        scheduler.advance_to(scheduler.now_ns + duration).unwrap();
        let records = completion_records(&scheduler, &plan, fence, 0);
        for lane in &plan.lanes {
            let index = handles.iter().position(|h| *h == lane.request).unwrap();
            if records[lane.request.slot as usize].generated_tokens > 0
                && first_output_ns[index].is_none()
            {
                first_output_ns[index] = Some(scheduler.now_ns);
                first_output_prefill_dispatch[index] = Some(prefill_slots.len());
                if prefix_at_first_output.is_none() {
                    prefix_at_first_output = Some(prefill_slots.clone());
                    progressed_at_first_output = Some(consumed.clone());
                }
            }
        }
        complete_timed(&mut scheduler, &plan, fence, 0, true, gpu_time(duration));
        dispatches += 1;
    }
    assert!(handles.iter().all(|h| scheduler.request(*h).is_err()));
    assert!(first_output_ns.iter().all(Option::is_some));
    assert_eq!(consumed, vec![32768; count]);
    let progressed = progressed_at_first_output.unwrap();
    assert!(progressed.iter().all(|tokens| *tokens > 0));
    let prefix = prefix_at_first_output.unwrap();
    println!("B12X_PREFILL_TRACE {}", serde_json::json!({
        "policy": policy_name,
        "active_requests": count,
        "prompt_tokens_per_request": 32768,
        "output_budget": 1,
        "prefill_chunk": 4096,
        "fixture": "pinned interactive_engine; ordinary graphs; synthetic costs; one in-flight submission",
        "qualification": "CPU scheduling behavior only; not GPU speed or full native runtime causality",
        "first_output_synthetic_ns": first_output_ns,
        "first_output_prefill_dispatch": first_output_prefill_dispatch,
        "consumed_at_first_output": progressed,
        "prefill_slots": prefill_slots,
        "prefix_at_first_output": prefix,
        "dispatches": dispatches
    }));
    prefix
}

#[test]
fn pure_prefill_presets_have_the_same_service_prefix() {
    for count in [1, 2, 4] {
        let balanced = prefill_trace("balanced", PolicyConfig::default(), count);
        let throughput = prefill_trace("throughput", PolicyConfig::throughput(), count);
        assert_eq!(balanced, throughput,
            "the presets differ before any decoder exists; investigate before claiming equivalence");
    }
}
