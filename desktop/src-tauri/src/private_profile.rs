use std::{ffi::OsStr, path::PathBuf};
use tauri::utils::config::WindowConfig;
use uuid::Uuid;

pub const DEFAULT_SERVICE: &str = "io.havesomecode.omr";

pub fn take_windows(windows: &mut Vec<WindowConfig>, profile: Option<Uuid>) -> Vec<WindowConfig> {
    if profile.is_some() {
        std::mem::take(windows)
    } else {
        Vec::new()
    }
}

pub fn select(value: Option<&OsStr>) -> Result<Option<Uuid>, &'static str> {
    let Some(value) = value else { return Ok(None) };
    let name = value.to_str().ok_or("invalid_config")?;
    let id = Uuid::parse_str(name).map_err(|_| "invalid_config")?;
    if id.is_nil() || id.to_string() != name {
        return Err("invalid_config");
    }
    Ok(Some(id))
}

pub fn prepare(base: PathBuf, profile: Option<Uuid>) -> Result<(PathBuf, String), &'static str> {
    let Some(id) = profile else {
        return Ok((base, DEFAULT_SERVICE.into()));
    };
    #[cfg(not(unix))]
    {
        let _ = id;
        Err("storage_unavailable")
    }
    #[cfg(unix)]
    {
        use std::{
            fs,
            io::ErrorKind,
            os::unix::fs::{DirBuilderExt, MetadataExt, PermissionsExt},
        };
        unsafe extern "C" {
            fn geteuid() -> u32;
        }
        // The UID is platform metadata; no credential contents or Keychain settings are read.
        let uid = unsafe { geteuid() };
        for ancestor in base.ancestors() {
            match fs::symlink_metadata(ancestor) {
                Ok(meta) if meta.is_symlink() || !meta.is_dir() => {
                    return Err("storage_unavailable")
                }
                Ok(_) => (),
                Err(error) if error.kind() == ErrorKind::NotFound => (),
                Err(_) => return Err("storage_unavailable"),
            }
        }
        let safe = |path: &std::path::Path, private: bool| -> Result<(), &'static str> {
            let meta = fs::symlink_metadata(path).map_err(|_| "storage_unavailable")?;
            let mode = meta.permissions().mode() & 0o777;
            if meta.is_symlink()
                || !meta.is_dir()
                || meta.uid() != uid
                || (private && mode != 0o700)
                || (!private && mode & 0o022 != 0)
            {
                return Err("storage_unavailable");
            }
            Ok(())
        };
        if base.exists() {
            safe(&base, false)?;
        }
        fs::DirBuilder::new()
            .recursive(true)
            .mode(0o700)
            .create(&base)
            .map_err(|_| "storage_unavailable")?;
        safe(&base, false)?;
        let directory = base.join("profiles").join(id.to_string());
        for path in [base.join("profiles"), directory.clone()] {
            match fs::DirBuilder::new().mode(0o700).create(&path) {
                Ok(()) => (),
                Err(error) if error.kind() == ErrorKind::AlreadyExists => (),
                Err(_) => return Err("storage_unavailable"),
            }
            safe(&path, true)?;
        }
        Ok((directory, format!("{DEFAULT_SERVICE}.profile.{id}")))
    }
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;
    use std::{
        fs,
        os::unix::fs::{symlink, PermissionsExt},
    };

    fn scratch() -> PathBuf {
        let root = std::env::temp_dir().join(format!("omr-profile-{}", Uuid::new_v4()));
        fs::create_dir(&root).unwrap();
        root.canonicalize().unwrap()
    }

    #[test]
    fn private_windows_cannot_be_created_by_the_default_store_path() {
        let mut windows = vec![WindowConfig::default()];
        windows[0].label = "main".into();
        windows[0].visible = false;
        assert!(take_windows(&mut windows, None).is_empty());
        assert_eq!(windows.len(), 1);
        let private = take_windows(&mut windows, Some(Uuid::new_v4()));
        assert!(
            windows.is_empty(),
            "private windows must leave the automatic creation path"
        );
        assert_eq!(private.len(), 1);
        assert_eq!(private[0].label, "main");
        assert!(!private[0].visible);
    }

    #[test]
    fn default_is_unchanged_and_invalid_selectors_fail_closed() {
        let base = PathBuf::from("never-created-default");
        assert_eq!(
            prepare(base.clone(), None).unwrap(),
            (base, DEFAULT_SERVICE.into())
        );
        assert_eq!(select(None).unwrap(), None);
        let id = Uuid::parse_str("d270b8d6-aac1-4a2a-95c9-424dd13af871").unwrap();
        assert_eq!(select(Some(OsStr::new(&id.to_string()))).unwrap(), Some(id));
        for value in [
            "",
            ".",
            "..",
            "../../default",
            "test/profile",
            "not-a-uuid",
            "00000000-0000-0000-0000-000000000000",
        ] {
            assert!(select(Some(OsStr::new(value))).is_err(), "{value}");
        }
        assert!(select(Some(OsStr::new(&id.to_string().to_uppercase()))).is_err());
        use std::os::unix::ffi::OsStrExt;
        assert!(select(Some(OsStr::from_bytes(&[0xff]))).is_err());
    }

    #[test]
    fn private_data_and_services_are_disjoint_and_stable() {
        let root = scratch();
        fs::write(root.join("providers.json"), b"unchanged normal profile").unwrap();
        let original_mode = fs::metadata(&root).unwrap().permissions().mode();
        let first = Uuid::new_v4();
        let second = Uuid::new_v4();
        let a = prepare(root.clone(), Some(first)).unwrap();
        let b = prepare(root.clone(), Some(second)).unwrap();
        assert_eq!(a.0, root.join("profiles").join(first.to_string()));
        assert_eq!(a.1, format!("{DEFAULT_SERVICE}.profile.{first}"));
        assert_ne!(a, b);
        assert_eq!(prepare(root.clone(), Some(first)).unwrap(), a);
        for path in [root.join("profiles"), a.0, b.0] {
            assert_eq!(
                fs::metadata(path).unwrap().permissions().mode() & 0o777,
                0o700
            );
        }
        assert_eq!(
            fs::read(root.join("providers.json")).unwrap(),
            b"unchanged normal profile"
        );
        assert_eq!(
            fs::metadata(&root).unwrap().permissions().mode(),
            original_mode
        );
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn links_and_unsafe_permissions_are_refused_without_mutation() {
        let root = scratch();
        let base = root.join("app");
        let outside = root.join("outside");
        fs::create_dir(&base).unwrap();
        fs::create_dir(&outside).unwrap();
        fs::write(outside.join("sentinel"), b"untouched").unwrap();
        symlink(&outside, base.join("profiles")).unwrap();
        assert!(prepare(base.clone(), Some(Uuid::new_v4())).is_err());
        assert_eq!(fs::read(outside.join("sentinel")).unwrap(), b"untouched");
        fs::remove_file(base.join("profiles")).unwrap();
        fs::create_dir(base.join("profiles")).unwrap();
        fs::set_permissions(base.join("profiles"), fs::Permissions::from_mode(0o755)).unwrap();
        assert!(prepare(base.clone(), Some(Uuid::new_v4())).is_err());
        assert_eq!(
            fs::metadata(base.join("profiles"))
                .unwrap()
                .permissions()
                .mode()
                & 0o777,
            0o755
        );
        fs::set_permissions(base.join("profiles"), fs::Permissions::from_mode(0o700)).unwrap();
        let id = Uuid::new_v4();
        symlink(&outside, base.join("profiles").join(id.to_string())).unwrap();
        assert!(prepare(base.clone(), Some(id)).is_err());
        let alias = root.join("app-alias");
        symlink(&base, &alias).unwrap();
        assert!(prepare(alias, Some(Uuid::new_v4())).is_err());
        fs::set_permissions(&base, fs::Permissions::from_mode(0o777)).unwrap();
        assert!(prepare(base.clone(), Some(Uuid::new_v4())).is_err());
        fs::set_permissions(base, fs::Permissions::from_mode(0o700)).unwrap();
        fs::remove_dir_all(root).unwrap();
    }
}
