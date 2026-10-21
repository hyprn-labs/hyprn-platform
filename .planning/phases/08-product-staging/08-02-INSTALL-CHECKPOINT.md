# Authenticated native release staging prerequisite

Source `d786890`. Parent committed check `tests/platform/run.sh install`:
10 passed, 0 failed, 0 skipped, 0.014 seconds. Actual temporary tar archives and
filesystem operations are used; no executable inside an archive is launched.
All temporary scopes are released by fixture cleanup.

`host/install_release.py` reuses the contract's archive authentication and safety
checks, retains the opened inode, validates build prefix/source/target and every
inventory hash, writes only a fresh temporary release tree, syncs files/directories,
and renames into the exact final prefix. Existing destinations are refused.
Wrong hashes, traversal, extra members, unexpected writable paths and links fail
without replacing any other release. Unsuccessful extraction removes only its
own temporary directory. The caller must retain the deployment lock.

This is a trusted-bootstrap primitive, not a complete installer or an authority
to run downloaded code. Bootstrap must supply reviewed immutable descriptors and
protected destination policy. No cloud download, image load, secret access,
service start, admission change or live filesystem mutation was performed.
An installed exact native bundle must still pass the existing Linux import/
execution qualification at its recorded prefix before activation. Whole host
bootstrap, firewall/egress qualification, second activation and recovery remain
parent-owned; this does not close 08-02.
