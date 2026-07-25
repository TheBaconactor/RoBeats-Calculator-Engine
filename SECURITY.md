# Security policy

## Supported versions

Security fixes are applied to the latest revision of the `main` branch. Older commits and local forks are not supported.

## Reporting a vulnerability

Please do not disclose a suspected vulnerability in a public issue, discussion, or pull request.

Use GitHub's private vulnerability reporting for this repository:

1. Open the repository's **Security** tab.
2. Select **Advisories**.
3. Select **Report a vulnerability**.

Include the affected component, reproduction steps, potential impact, and any suggested mitigation. Remove API tokens, frontier credentials, private chart uploads, and other sensitive data from logs or screenshots.

If private vulnerability reporting is unavailable, contact the repository owner through their [GitHub profile](https://github.com/TheBaconactor) before sharing technical details publicly.

You can expect an acknowledgement after the report has been reviewed. Resolution timelines depend on severity and the complexity of a safe fix.

## Deployment guidance

- Bind the optimizer HTTP service to loopback unless it is protected by a trusted network boundary.
- Set `ROBEATSMETA_OPTIMIZER_API_TOKEN` before exposing the service to a network.
- Never commit API tokens, frontier credentials, client registries, private uploads, or deployment secrets.
- Rotate a credential immediately if it is exposed, including exposure in Git history.
