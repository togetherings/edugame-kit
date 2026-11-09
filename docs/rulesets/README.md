# Rulesets for game repositories

Two GitHub rulesets that protect a repository's `main` branch. Import one in a repository's
**Settings > Rules > Rulesets > New ruleset > Import a ruleset**.

| File | For | Rules |
|---|---|---|
| `protect-main.json` | every repository with code: games, the kit, the plugin | `main` can't be deleted or force-pushed; changes reach it only through a pull request (no approval needed); the check **Checks passed** must pass first |
| `protect-main-generated.json` | a repository a workflow writes to, like edugame-template | `main` can't be deleted or force-pushed |

Repository admins can bypass both, for emergencies (GitHub asks first).

**Checks passed** is a job every repository's test workflow has: it waits for the other test jobs and passes only
if they all did. So the same ruleset fits every repository, and tests can be added or renamed without changing it.
Games made with `edugame new --github` (or from edugame-template) have it already: their Build workflow's job is
named **Checks passed**. A repository without such a job can't merge pull requests under `protect-main.json`.
