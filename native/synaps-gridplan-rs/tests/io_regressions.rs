use synaps_gridplan_rs::read_text_limited;
use synaps_gridplan_rs::sanitize::display_text;

#[test]
fn read_text_limited_caps_bytes_actually_read() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("blob.txt");
    std::fs::write(&path, b"ab").unwrap();
    assert_eq!(read_text_limited(&path, 2).unwrap(), "ab");
    std::fs::write(&path, b"abc").unwrap();
    let err = read_text_limited(&path, 2).unwrap_err();
    assert!(err.contains("limit is 2"), "{err}");
}

#[test]
fn display_text_flattens_newlines_html_and_backticks() {
    assert_eq!(display_text("line1\nline2"), "line1 line2");
    assert_eq!(display_text("a`b"), "a'b");
    assert_eq!(
        display_text("<script>x</script>"),
        "&lt;script&gt;x&lt;/script&gt;"
    );
}

#[test]
fn small_synthetic_does_not_mark_windows_frozen() {
    let p = synaps_gridplan_rs::synthesize_feeder("small", 12, None, None, None).unwrap();
    assert!(!p.outage_windows.is_empty());
    assert!(p.outage_windows.iter().all(|window| !window.frozen));
}
