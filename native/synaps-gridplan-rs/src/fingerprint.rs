//! Stable digests — byte-compatible with Python `synaps_gridplan.fingerprint`.

use serde_json::Value;
use sha2::{Digest, Sha256};

/// SHA-256 hex (truncated) of parts joined by U+001F.
pub fn stable_digest(parts: &[&str], length: usize) -> String {
    let payload = parts.join("\u{001f}");
    let hex = format!("{:x}", Sha256::digest(payload.as_bytes()));
    hex.chars().take(length).collect()
}

/// Deterministic non-negative integer in `[0, modulo)`.
pub fn stable_int(parts: &[&str], modulo: u64) -> u64 {
    assert!(modulo > 0, "modulo must be positive");
    let payload = parts.join("\u{001f}");
    let digest = Sha256::digest(payload.as_bytes());
    let mut buf = [0u8; 8];
    buf.copy_from_slice(&digest[..8]);
    u64::from_be_bytes(buf) % modulo
}

/// Canonical JSON (sorted keys, compact) then SHA-256 full hex.
pub fn fingerprint_payload(value: &Value) -> String {
    let canon = canonical_json(value);
    format!("{:x}", Sha256::digest(canon.as_bytes()))
}

fn canonical_json(value: &Value) -> String {
    match value {
        Value::Null => "null".to_string(),
        Value::Bool(b) => b.to_string(),
        Value::Number(n) => n.to_string(),
        Value::String(s) => serde_json::to_string(s).unwrap_or_else(|_| "\"\"".into()),
        Value::Array(arr) => {
            let parts: Vec<String> = arr.iter().map(canonical_json).collect();
            format!("[{}]", parts.join(","))
        }
        Value::Object(map) => {
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort();
            let parts: Vec<String> = keys
                .into_iter()
                .map(|k| {
                    let key = serde_json::to_string(k).unwrap_or_else(|_| "\"\"".into());
                    format!("{}:{}", key, canonical_json(&map[k]))
                })
                .collect();
            format!("{{{}}}", parts.join(","))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn stable_int_matches_python_fixture() {
        // Precomputed with Python synaps_gridplan.fingerprint.stable_int
        assert_eq!(stable_int(&["42", "LOC-1", "LOC-2"], 45), 34);
    }

    #[test]
    fn fingerprint_simple_object() {
        let v = json!({"b": 2, "a": 1});
        let h = fingerprint_payload(&v);
        assert_eq!(h.len(), 64);
        // canonical {"a":1,"b":2} — matches Python fingerprint_payload
        assert_eq!(
            h,
            "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
        );
    }
}
