# Step CA Implementation Notes

## What is Step CA?
Step CA is an open-source Certificate Authority (CA) that makes internal SSL/TLS certificate management much simpler. Think of it as "Let's Encrypt for internal networks". It's maintained by the Smallstep team (former Google/AWS/Mozilla engineers).

## Why Use Step CA?
1. Current Problem:
   - Each device needs manual certificate installation
   - Android tablets aren't domain-joined
   - Certificate renewal is manual
   - No central management

2. Benefits:
   - Automatic certificate renewal
   - One-time root CA installation
   - Works with any device (including Android tablets)
   - No public domain needed
   - Full control over certificate policies
   - API for programmatic certificate management

## Implementation Plan

### 1. Docker Setup
Add to docker-compose-PROD.yml:
```yaml
services:
  step-ca:
    image: smallstep/step-ca
    container_name: step-ca
    volumes:
      - ./step:/home/step
    ports:
      - "9000:9000"
    environment:
      - DOCKER_STEPCA_INIT_NAME=Kinpak Internal CA
      - DOCKER_STEPCA_INIT_DNS_NAMES=192.168.178.169
```

### 2. Certificate Management
- Initial setup creates root CA
- Nginx gets certificates automatically
- Certificates auto-renew before expiry
- Root CA certificate distributed once to devices

### 3. Device Enrollment
1. Create simple enrollment page at https://192.168.178.169:1338/cert
2. Users visit once to install root CA
3. All future certificates trusted automatically

### 4. Integration with Current Setup
- Works with current nginx configuration
- Blue/Green deployment compatible
- No changes needed to Django application

### 5. Maintenance
- Certificates renew automatically
- Root CA valid for 10 years
- Backup root CA keys in secure location

## Security Notes
- Keep root CA key secure
- Regular backups of /step volume
- Monitor certificate renewals
- Document recovery procedures

## Resources
- Step CA Documentation: https://smallstep.com/docs/step-ca
- GitHub Repo: https://github.com/smallstep/certificates