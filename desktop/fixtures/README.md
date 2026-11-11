# Synthetic public CA fixture

`test-ca.pem` is a self-signed public certificate named **OMR Synthetic Test CA**, generated only to test loading certificate roots in the frozen-engine contract. It is not a production CA and is never included in the application's trust bundle. No corresponding private key belongs in Git. Production packages use the separately pinned certifi trust bundle and its license.
