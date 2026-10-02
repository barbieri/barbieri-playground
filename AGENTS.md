# Contributor guide

This repository holds independent experiments and reusable agent skills. Read the
README or instructions in the subproject you change before editing it. Use that
subproject's build and test commands; there is no repository-wide QA command.

## Agent skills

For nontrivial implementation work, load `.agents/skills/poteto-mode/SKILL.md`
before work and run `.agents/skills/thermos/SKILL.md` before handoff. Use
`.agents/skills/code-review/SKILL.md` for a branch review when an originating
request or spec is available. Its issue-tracker setup lives in
`.agents/skills/setup-matt-pocock-skills/SKILL.md` and `docs/agents/`.

For Codex, use native subagents for upstream `Task` roles. In Thermos, give
one reviewer `.agents/skills/thermo-nuclear-review/SKILL.md` and another
`.agents/skills/thermo-nuclear-code-quality-review/SKILL.md`, then synthesize
their findings.

Before a pull request, compare every commit with the branch's merge-base. A
correction to code introduced by an earlier commit in the same branch belongs
in that introducing commit. Use a fixup and autosquash before publishing.
Keep a separate commit for an independent improvement or a fix to code from
the base branch. Run the relevant checks for each finished commit and review
the final diff. Use `.agents/skills/git-history-cleanup/SKILL.md` only when a
private, linear series needs broader regrouping.

Add a test only when it proves a distinct behavior or regression that existing
tests do not cover. A test must check an observable result, not mirror the
implementation.

## Self-update

After a failure, review, or other discovery, record a durable lesson in the
source document that owns it. Put subproject behavior in its own documentation.
Put reusable contributor procedure here or in a skill owned by this repository.
Use `.agents/skills/reflect/SKILL.md` for a substantial lesson review. Fold a
lesson into the relevant original commit before publishing, usually the first
workflow commit when it applies to the whole series.

Never use this self-update process to edit installed skills under
`~/.agent/skills/`, `~/.agents/skills/`, or project `.agents/skills/`
when a skill lock tracks them and the source is not ours. For a skill
owned here, edit its source under `skills/`,
open a pull request, and let the owner review and merge it. Only then update
the installed copy in consuming repositories with `npx skills update`.

GitHub issues are the issue tracker for this repository. See
`docs/agents/issue-tracker.md`. The default triage label mapping is in
`docs/agents/triage-labels.md`. Domain-document routing is in
`docs/agents/domain.md`.
