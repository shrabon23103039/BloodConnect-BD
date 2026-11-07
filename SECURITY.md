# Security policy

## Scope

This project is an academic MVP/local demonstration. It is not currently a hosted production service. Supported fixes are made against the current `master` branch; there are no tagged releases or versioned support branches yet.

## Report a vulnerability privately

Please do not open a public issue or pull request for a suspected vulnerability. Use GitHub's **Report a vulnerability** / private vulnerability reporting feature for this repository if it is enabled. If that option is unavailable, contact the repository maintainer privately through GitHub before sharing technical details.

Include a concise description, affected component, reproduction steps using synthetic data, and potential impact. Do not include donor/requester contact details, health information, real credentials, tokens, private URLs, or production data. Redact logs and screenshots before sharing.

The maintainer will acknowledge reports and coordinate triage on a best-effort basis. No response-time SLA or dedicated incident-response service is currently promised. Please allow time for investigation and coordinated remediation before public disclosure.

## Security boundaries

- Never test against real donor/requester records or a production service without written authorization.
- Do not attempt denial-of-service, social engineering, credential stuffing, or access to another person's account/data.
- The platform does not determine medical eligibility, compatibility, blood availability, or transfusion safety.
- Account verification and outbound email/SMS remain mock-only or disabled until an authorized provider is implemented.

See `docs/07_Security.md` and `docs/11_Data_Governance.md` for the project's security and privacy constraints.
