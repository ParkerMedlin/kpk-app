# Kinpak Internal TLS Playbook

This workflow replaces the ad-hoc “exceladdin” certificates with an internal CA that can issue trusted
certificates for `kpkapp.lan` and any subdomain you stand up (e.g. `rpm.kpkapp.lan`).
Certificates live in `nginx/ssl/` but are generated locally so private keys stay off of Git.

## 1. Generate / refresh certificates

```bash
# From the repo root
bash scripts/tls/generate-internal-certs.sh
```

What the script does:
- creates (or reuses) `nginx/ssl/kpkapp-rootCA.crt` and `.key`
- issues `kpkapp.lan.crt`, `kpkapp.lan.key`, plus chain/PEM bundles with SANs for:
  - `kpkapp.lan`, `*.kpkapp.lan`
  - `rpm.kpkapp.lan`
  - 192.168.178.168 and 192.168.178.169

Environment overrides:

```bash
SERVER_HOSTS="kpkapp.lan,*.kpkapp.lan,staging.kpkapp.lan" \
SERVER_IPS="192.168.178.168" \
bash scripts/tls/generate-internal-certs.sh
```

> **Important:** Protect `nginx/ssl/kpkapp-rootCA.key`. It should live in a secrets manager (1Password/Bitwarden) and
> never be emailed or committed.

## 2. Distribute the root CA

All clients must trust `nginx/ssl/kpkapp-rootCA.crt`. The easiest path is to automate the install per platform.

### Windows (domain joined)

1. Copy `nginx/ssl/kpkapp-rootCA.crt` to a network share.
2. Run `local_machine_scripts/python_systray_scripts/install-root-ca.ps1` as admin, or push it via GPO:

   ```powershell
   powershell -ExecutionPolicy Bypass -File \\share\install-root-ca.ps1 -CaPath \\share\kpkapp-rootCA.crt
   ```
3. Verify with `certmgr.msc` → Trusted Root Certification Authorities → Certificates → look for “Kinpak Internal Root CA”.

### Windows (single box / dev)

```powershell
Set-Location C:\Users\%USERNAME%\Documents\kpk-app
.\local_machine_scripts\python_systray_scripts\install-root-ca.ps1
```

### macOS

```bash
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  nginx/ssl/kpkapp-rootCA.crt
```

### iOS / iPadOS

1. Have users download `https://kpkapp.lan/cert` from Safari.
2. Open the URL on the device; iOS will prompt to install the profile.
3. Go to *Settings → General → About → Certificate Trust Settings* and toggle “Full Trust” for the new CA.

## 3. Rebuild and deploy nginx

After generating certificates or rotating SANs:

```bash
docker compose -f docker-compose-PROD.yml build nginx
docker compose -f docker-compose-PROD.yml up -d nginx
```

Then validate:

```bash
curl -Ik https://kpkapp.lan/
# Expect HTTP/1.1 200 OK and the certificate subject CN=kpkapp.lan
```

## 4. Renewal cadence

- Root CA: 10-year default (override with `CA_VALID_DAYS` if needed).
- Server certificates: 825 days by default (`SERVER_VALID_DAYS`).
- Add a calendar reminder or CI check that runs
  `openssl x509 -checkend 2592000 -noout -in nginx/ssl/kpkapp.lan.crt` to warn ~30 days before expiry.

## 5. Recovery / rotation

If the CA key is ever compromised, regenerate from scratch:

1. Revoke access to the old `kpkapp-rootCA.key`.
2. Delete `nginx/ssl/kpkapp-rootCA.*` (keep a secure backup for forensics).
3. Re-run the generation script to mint a new CA + server cert.
4. Redeploy nginx and push the new root CA to clients (old certs must be removed from trust stores).

## 6. Quick checklist for new environments

- [ ] Run `scripts/tls/generate-internal-certs.sh`.
- [ ] Install root CA on target devices.
- [ ] Ensure DNS (AD) resolves the hostname to the correct IP.
- [ ] Update `.env` / `ALLOWED_HOSTS` if introducing new subdomains.
- [ ] Rebuild & restart nginx.
- [ ] Smoke test with `curl` and Chrome/Safari (no certificate warnings).
