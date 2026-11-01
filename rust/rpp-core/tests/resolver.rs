use rpp_core::resolver::{
    resolve, AccessGate, AttemptOutcome, AttemptResult, DiscoveredEndpoint, Modality,
    ResolutionErrorCode,
};

fn endpoint(modality: Modality) -> DiscoveredEndpoint {
    DiscoveredEndpoint {
        modality,
        uri: format!("{}://fixture/path", modality.scheme()),
        available: true,
    }
}

fn outcome(modality: Modality, result: AttemptResult) -> AttemptOutcome {
    AttemptOutcome { modality, result }
}
fn permitted() -> AccessGate {
    AccessGate {
        authorized: true,
        consented: true,
    }
}

/// Failing mutation: use discovery order instead of the caller's preference order.
#[test]
fn selection_uses_explicit_preferences_then_environment_defaults() {
    let discovered = [endpoint(Modality::Ipv4), endpoint(Modality::Bluetooth)];
    let outcomes = [
        outcome(Modality::Ipv4, AttemptResult::Found),
        outcome(Modality::Bluetooth, AttemptResult::Found),
    ];
    let preferences = [Modality::Bluetooth, Modality::Ipv4];
    let selected = resolve(
        &discovered,
        Some(&preferences),
        &[Modality::Ipv4],
        &outcomes,
        permitted(),
    )
    .unwrap();
    assert_eq!(selected.modality, Modality::Bluetooth);
    assert_eq!(selected.tried_modalities, [Modality::Bluetooth]);
    let selected = resolve(&discovered, None, &[Modality::Ipv4], &outcomes, permitted()).unwrap();
    assert_eq!(selected.modality, Modality::Ipv4);
}

/// Failing mutation: stop on NotFound/unavailable or omit failed attempts from history.
#[test]
fn fallback_tracks_unavailable_and_not_found_modalities() {
    let discovered = [endpoint(Modality::File), endpoint(Modality::Bluetooth)];
    let outcomes = [
        outcome(Modality::File, AttemptResult::NotFound),
        outcome(Modality::Bluetooth, AttemptResult::Found),
    ];
    let order = [Modality::Ipv6, Modality::File, Modality::Bluetooth];
    let selected = resolve(&discovered, None, &order, &outcomes, permitted()).unwrap();
    assert_eq!(selected.modality, Modality::Bluetooth);
    assert_eq!(selected.tried_modalities, order);
    let outcomes = [
        outcome(Modality::File, AttemptResult::Unavailable),
        outcome(Modality::Bluetooth, AttemptResult::Found),
    ];
    assert_eq!(
        resolve(&discovered, None, &order, &outcomes, permitted())
            .unwrap()
            .tried_modalities,
        order
    );
}

/// Failing mutation: select a route despite missing consent/trust or retry after denial.
#[test]
fn consent_trust_and_adapter_denials_are_terminal() {
    let discovered = [endpoint(Modality::Ipv4), endpoint(Modality::Bluetooth)];
    let order = [Modality::Ipv4, Modality::Bluetooth];
    let found = [outcome(Modality::Ipv4, AttemptResult::Found)];
    for (gate, expected) in [
        (
            AccessGate {
                authorized: true,
                consented: false,
            },
            ResolutionErrorCode::ConsentDenied,
        ),
        (
            AccessGate {
                authorized: false,
                consented: true,
            },
            ResolutionErrorCode::TrustDenied,
        ),
    ] {
        let denied = resolve(&discovered, None, &order, &found, gate).unwrap_err();
        assert_eq!(denied.code, expected);
        assert!(denied.tried_modalities.is_empty());
    }
    let denied = resolve(
        &discovered,
        None,
        &order,
        &[
            outcome(Modality::Ipv4, AttemptResult::Denied),
            outcome(Modality::Bluetooth, AttemptResult::Found),
        ],
        permitted(),
    )
    .unwrap_err();
    assert_eq!(denied.code, ResolutionErrorCode::AdapterDenied);
    assert_eq!(denied.tried_modalities, [Modality::Ipv4]);
}

/// Failing mutation: invent success for absent discovery, absent outcome or UNKNOWN.
#[test]
fn exhausted_or_missing_inputs_return_explicit_no_modality() {
    let order = [Modality::Unknown, Modality::Ipv4, Modality::Ipv4];
    let failed = resolve(
        &[endpoint(Modality::Unknown), endpoint(Modality::Ipv4)],
        None,
        &order,
        &[],
        permitted(),
    )
    .unwrap_err();
    assert_eq!(failed.code, ResolutionErrorCode::NoModality);
    assert_eq!(failed.tried_modalities, [Modality::Unknown, Modality::Ipv4]);
    assert_eq!(
        resolve(&[], None, &[], &[], permitted()).unwrap_err().code,
        ResolutionErrorCode::NoModality
    );
    assert_eq!(
        resolve(
            &[endpoint(Modality::Ipv4)],
            Some(&[]),
            &[Modality::Ipv4],
            &[outcome(Modality::Ipv4, AttemptResult::Found)],
            permitted()
        )
        .unwrap_err()
        .code,
        ResolutionErrorCode::NoModality
    );
}

/// Failing mutation: accept a mismatched URI scheme or unavailable discovery record.
#[test]
fn discovery_uri_and_availability_filter_before_success() {
    let order = [Modality::Ipv4, Modality::Bluetooth];
    let found = [
        outcome(Modality::Ipv4, AttemptResult::Found),
        outcome(Modality::Bluetooth, AttemptResult::Found),
    ];
    let bad = DiscoveredEndpoint {
        modality: Modality::Ipv4,
        uri: "bt://wrong-profile".into(),
        available: true,
    };
    assert_eq!(
        resolve(
            &[bad, endpoint(Modality::Bluetooth)],
            None,
            &order,
            &found,
            permitted()
        )
        .unwrap()
        .modality,
        Modality::Bluetooth
    );
    let unavailable = DiscoveredEndpoint {
        modality: Modality::Ipv4,
        uri: "ipv4://fixture".into(),
        available: false,
    };
    assert_eq!(
        resolve(
            &[unavailable, endpoint(Modality::Bluetooth)],
            None,
            &order,
            &found,
            permitted()
        )
        .unwrap()
        .modality,
        Modality::Bluetooth
    );
}

/// Failing mutation: invalid-first-shadows-valid by validating only after find.
#[test]
fn invalid_first_candidate_does_not_shadow_valid_same_modality() {
    let wrong_scheme = DiscoveredEndpoint {
        modality: Modality::Ipv4,
        uri: "bt://wrong-profile".into(),
        available: true,
    };
    let empty = DiscoveredEndpoint {
        modality: Modality::Ipv4,
        uri: "ipv4://".into(),
        available: true,
    };
    let selected = resolve(
        &[wrong_scheme, empty, endpoint(Modality::Ipv4)],
        None,
        &[Modality::Ipv4, Modality::Bluetooth],
        &[outcome(Modality::Ipv4, AttemptResult::Found)],
        permitted(),
    )
    .unwrap();
    assert_eq!(selected.modality, Modality::Ipv4);
    assert_eq!(selected.uri, "ipv4://fixture/path");
    assert_eq!(selected.tried_modalities, [Modality::Ipv4]);
}
