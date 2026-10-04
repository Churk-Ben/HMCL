# HMCL Experimental Channel (Unofficial)

> [!IMPORTANT]
> **This is not an official project.**
> This repository is a community-maintained, experimental downstream fork of HMCL and has no affiliation with
> [HMCL-dev/HMCL](https://github.com/HMCL-dev/HMCL). Builds published here may add or remove features at any time
> and are **not** supported by the HMCL team. For the official launcher, visit
> <https://github.com/HMCL-dev/HMCL> or <https://hmcl.huangyuhui.net>.

New here? Please read this whole document before using or contributing.

## What this is

This fork aggressively tracks the upstream project. It merges upstream `main` frequently, integrates pending
upstream pull requests early, and ships builds from its own `experimental` channel. As a result:

- features can appear and disappear between releases;
- a feature that is still experimental may be removed once upstream adopts a different design, or once a
  tracked pull request is merged upstream and the fork can drop its own copy;
- there is no stability guarantee.

If you want a stable, officially supported launcher, use the official project instead.

## Update channel

The launcher exposes a first-class **Experimental** channel alongside Stable and Development.

| Property | Value |
| --- | --- |
| Channel identifier | `experimental` |
| Display name | Experimental / 实验版 / 實驗版 |
| Artifact naming | `HMCL-<main version>-<build number>.exp.<short SHA>.<ext>` |
| Linux package name | `hmcl-exp` |
| Linux command | `hmcl-exp` |
| Linux per-instance data directory | `$HMCL_USER_HOME/local-exp` |
| Update metadata | `update-exp.json` on the latest release |

Experimental builds are **pinned to the Experimental channel**, similar to a canary channel. The channel
selector is locked and there is no in-app downgrade path: to return to Stable or Development, uninstall this
fork and install the official build.

## Branch model

| Branch | Purpose |
| --- | --- |
| `main` | Mirror of upstream `HMCL-dev/HMCL` `main`. Do not develop here. |
| `experimental` | Integration branch and default branch. Releases are built from here. |
| `pr/<number>-<slug>` | One branch per upstream/fork pull request. |
| `workspace/<name>` | Automated maintenance branches (upstream sync, daily aggregation). Opened as pull requests against `experimental`. |

Lifecycle of a tracked feature:

1. It lives on a `pr/*` branch and is integrated into `experimental`.
2. When the equivalent pull request is merged upstream, the fork drops its copy and deletes the branch.
3. Upstream `main` is merged into `experimental` regularly so dropped features come from upstream instead.

## Release policy

Releases are intended to be produced **daily** by an automated workflow, and can also be triggered manually.
Each release can aggregate a small number of high-priority upstream pull requests on top of upstream `main`,
together with this fork's own changes. The exact selection rule and how manual additions/removals are specified
are still being defined.

## Contributing

Community contributions are welcome, with the understanding that the merge policy is aggressive and features
may be short-lived.

- Feature work: open a pull request targeting `experimental`.
- Branch naming: `pr/*` for features, `workspace/*` for automated maintenance.
- Expect changes to be reworked or removed if upstream adopts a different solution.

## Returning to the official launcher

1. Uninstall this fork (for example `sudo dnf remove hmcl-exp`).
2. Install the official release from <https://hmcl.huangyuhui.net/download>.
3. If you want to keep your accounts and settings, they live in `~/.local/share/hmcl` and are shared with the
   official launcher; never delete that directory unless you intend to reset everything.
