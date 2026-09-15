# Cross-Machine Git Checklist

This repo is worked on from two machines under one contributor (`jaxub96-WINDOWS`
and `jeanKoby-MAC`).

To prevent unsynced work, follow the checklist before work.

## Before starting work on a machine

1. `git status` - if anything is uncommitted from last time, deal with it
   first (commit, stash, or discard on purpose). Don't start new work on
   top of unknown local state.
2. `git fetch origin` then `git log HEAD..origin/main --oneline` -
   see what's incoming *before* pulling. If it's non-empty, this machine
   was behind.
3. `git pull` (or `merge`/`rebase`, your call) and actually read the
   diff of what just came in (`git show <merge-commit>` or
   `git log -p -1`) for anything touching `addons/` or `modules/` - a
   new file or module you don't recognize is exactly the
   `asset_library.py` scenario repeating.
4. Skim `documentation/PROJECT_STATUS_AND_ROADMAP.md`'s "shipped"
   section if it's been a while - it's the fastest way to notice this
   machine is missing a feature the other one already has.

## Before switching away from a machine

5. Commit or stash (`git stash -u` if there are untracked files worth
   keeping) - never leave real work sitting uncommitted when you close
   the lid. The other machine can't see it, and it's easy to forget it's
   there.
6. `git push`. An unpushed local commit is the other machine's next
   "missing feature" surprise.

## Periodically

7. `git branch -a` - check `backup-before-reset` (or any other stray
   branch) isn't quietly diverging further from `main`; delete or merge
   it once it's no longer needed rather than letting it linger.
8. If a machine turns out to have been behind for a while, don't just
   pull and move on - grep the commits you missed for anything that
   should have changed how you'd been working locally in the meantime
   (a renamed API, like `zen_waypoint_links` replacing the old
   `modifiers`-based link storage, is exactly the kind of thing a stale
   checkout misses silently).
