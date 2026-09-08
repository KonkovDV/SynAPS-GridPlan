//! Flatten untrusted strings interpolated into Markdown reports.
//!
//! This is not a general HTML sanitizer. Interpolated values stay on one
//! visual line; backticks and angle brackets cannot change surrounding markup.

pub fn display_text(value: &str) -> String {
    value
        .replace(['\r', '\n'], " ")
        .replace('`', "'")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
}
