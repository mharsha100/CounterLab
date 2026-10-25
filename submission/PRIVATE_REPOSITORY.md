# Current GitHub handoff — private source only

The entrant authorized uploading the reviewed CounterLab source to their GitHub
account and **keeping the repository private for now**. No public website or
repository visibility change is authorized by that instruction.

The new source ZIP is the upload candidate. Credentials, private runtime history,
downloaded external code, dependency directories and the full upstream numeric
file are excluded. Original research/evaluation records retain their hashes and
real-versus-simulated labels. No API key needs to be added to GitHub.

## Before upload

1. Establish the GitHub connection in Codex and confirm the account login. No
   password or token needs to be pasted into this conversation.
2. Create or select the private CounterLab repository under that account.
3. Upload only the reviewed source package and verify the returned repository
   visibility is private, the source commit is present, and `.env` / full upstream
   reference / private histories are absent.
4. Leave Pages disabled. The included workflow is manual-only and additionally
   skips private repositories.

Connection and repository creation/upload are not completed merely because the
package or this checklist exists. Actual repository URL/commit/visibility must be
recorded from GitHub after the operation succeeds.

For final hackathon submission, public source and an accessible demo/test build
are still required. Make that transition only after a later explicit instruction,
then use `PUBLICATION_GUIDE.md` and verify the actual public links.
