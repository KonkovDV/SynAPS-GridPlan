use sha2::{Digest, Sha256};
use uuid::Uuid;

/// Same namespace as Python `synthetic._NS`.
pub const GRIDPLAN_NS: Uuid = Uuid::from_bytes([
    0xa1, 0xb2, 0xc3, 0xd4, 0xe5, 0xf6, 0x78, 0x90, 0xab, 0xcd, 0xef, 0x12, 0x34, 0x56, 0x78, 0x90,
]);

/// uuid5 matching Python `_uid(seed, *parts)`.
pub fn gridplan_uid(seed: u64, parts: &[&str]) -> Uuid {
    let name = format!("synaps-gridplan:{seed}:{}", parts.join(":"));
    Uuid::new_v5(&GRIDPLAN_NS, name.as_bytes())
}

/// Process-stable short token (not a UUID).
pub fn digest_token(parts: &[&str]) -> String {
    let payload = parts.join("\u{001f}");
    let hex = format!("{:x}", Sha256::digest(payload.as_bytes()));
    hex.chars().take(16).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn uuid5_matches_python_seed42_crew0() {
        let got = gridplan_uid(42, &["crew", "0"]);
        assert_eq!(
            got,
            Uuid::parse_str("5a64a413-e2cc-5aec-9336-a229cf7cfecd").unwrap()
        );
    }
}
