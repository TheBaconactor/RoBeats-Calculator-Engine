# Project governance

RoBeats Calculator Engine is an open-source, maintainer-led project. The Apache-2.0 license permits forks and independent modification; this governance policy controls the official repository, releases, services, data publications, and project identity.

## Roles

### Lead maintainer

The lead maintainer is the final authority for project direction, repository administration, maintainer appointments, security response, releases, official deployments, and use of project branding.

Current lead maintainer: [@TheBaconactor](https://github.com/TheBaconactor).

### Maintainers

Maintainers are explicitly appointed in [`MAINTAINERS.md`](MAINTAINERS.md) by the lead maintainer. They may review and merge only within their assigned scope. Repository activity, issue participation, prior contributions, or access to a fork does not create maintainer status.

### Contributors

Contributors may open issues, propose designs, submit pull requests, review public changes, and improve documentation. Contribution does not grant administrative, merge, release, deployment, credential, domain, or representational authority.

## Decision hierarchy

| Decision | Required authority |
|---|---|
| Documentation or isolated test improvements | Applicable code owner |
| Bug fixes within established behavior | Applicable maintainer and required checks |
| Scoring, timing, reachability, persistence, or schema semantics | Lead maintainer |
| Public API, data publication, security, or deployment changes | Lead maintainer |
| Releases, tags, signing, package publication, domains, credentials, or repository settings | Lead maintainer |
| Maintainer appointment, removal, or project transfer | Lead maintainer |

Consensus is preferred, but the lead maintainer has final decision authority when consensus is not reached or an invariant, security boundary, or project-scope question remains unresolved.

## Change control

- Changes to the official repository are made through pull requests.
- `CODEOWNERS` identifies required reviewers; branch protection must require code-owner approval.
- Authors cannot approve their own protected-surface changes.
- Force pushes, history rewrites, secret changes, branch-protection changes, release publication, and repository transfer are restricted to the lead maintainer.
- Scoring and persistence changes must identify the broken invariant, first violation point, fix shape, regression coverage, and complexity impact.
- Security reports follow [`SECURITY.md`](SECURITY.md) and remain private until coordinated disclosure is approved.

## Protected project assets

The following remain under lead-maintainer control:

- GitHub organization/repository administration and branch protection
- Official releases, tags, signing identities, and package namespaces
- `robeatsmeta.net`, its subdomains, production services, and deployment accounts
- API tokens, frontier credentials, registries, signing material, and operational secrets
- Canonical chart/data publications and production databases
- Official project name, logo, social accounts, announcements, and sponsorship applications

No contributor may claim to represent the project, publish an “official” build, request funds in the project’s name, or transfer an official asset without written authorization.

## Forks and unofficial distributions

Forks are permitted by the Apache-2.0 license. Forks must not imply endorsement, use official credentials, impersonate official services, or create confusion about which distribution is maintained here. Material modifications should be clearly identified.

## Succession

Project transfer or lead-maintainer succession requires an explicit written repository decision by the current lead maintainer. Inactivity alone does not transfer authority. If the official project becomes inactive, the license continues to permit independent forks without conferring control over official assets.
