fn main() {
    println!(
        "cargo:rustc-env=OMR_TARGET={}",
        std::env::var("TARGET").unwrap()
    );
    tauri_build::build()
}
