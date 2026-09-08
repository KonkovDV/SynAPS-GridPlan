//! Bounded file reads at the native CLI trust boundary.

use std::fs::File;
use std::io::Read;
use std::path::Path;

/// Read UTF-8 text, refusing anything larger than the lab quota.
///
/// The cap is applied to bytes actually read so a file that grows between
/// `stat` and `read` cannot bypass the quota.
pub fn read_text_limited(path: &Path, max_bytes: u64) -> Result<String, String> {
    let file = File::open(path).map_err(|e| e.to_string())?;
    let mut buf = Vec::new();
    file.take(max_bytes.saturating_add(1))
        .read_to_end(&mut buf)
        .map_err(|e| e.to_string())?;
    if (buf.len() as u64) > max_bytes {
        return Err(format!(
            "{} is larger than {max_bytes} bytes; limit is {max_bytes}",
            path.display()
        ));
    }
    String::from_utf8(buf).map_err(|e| e.to_string())
}
