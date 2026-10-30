# Current GitHub handoff — private source only

The entrant authorized uploading the reviewed CounterLab source to their GitHub
account and **keeping the repository private for now**. No public website or
repository visibility change is authorized by that instruction.

The new source ZIP is the upload candidate. Credentials, private runtime history,
downloaded external code, dependency directories and the full upstream numeric
file are excluded. Original research/evaluation records retain their hashes and
real-versus-simulated labels. No API key needs to be added to GitHub.

## Verified private upload — October 26, 2026

- Repository: https://github.com/mharsha100/CounterLab
- Default branch: `main`.
- Uploaded commit: `a9fe693cbc979c33097b824b8a6049c34788bd40`.
- Verified tree: `0c7626f8405cf953dcfbb40dfd1df2e0fa2bed7a`.
- All 295 archive files match the verified frozen source tree.
- Repository visibility after upload: **private**. No site deployment or
  workflow dispatch was requested.
- Receipt: `artifacts/releases/counterlab-private-sync-20261026/github-sync-receipt.json`.

This records the completed verification, not a guarantee that future repository
changes cannot occur. The frozen archives remain unchanged. Subsequent local
submission-document edits have not been uploaded to this commit.

The final project quality review also changes application code. Its new package
is `artifacts/releases/counterlab-final-review-20261026/`; that package needs a
new private sync. The receipt above proves only the preceding upload.

## Completed upload procedure

1. Establish the GitHub connection in Codex and confirm the account login. No
   password or token needs to be pasted into this conversation.
2. Create or select the private CounterLab repository under that account.
3. Upload only the reviewed source package and verify the returned repository
   visibility is private, the source commit is present, and `.env` / full upstream
   reference / private histories are absent.
4. Leave Pages disabled. The included workflow is manual-only and additionally
   skips private repositories.

The receipt above records the successful operation and subsequent visibility and
tree checks. A private repository is not yet a public source submission.

For final hackathon submission, public source and an accessible demo/test build
are still required. Make that transition only after a later explicit instruction,
then use `PUBLICATION_GUIDE.md` and verify the actual public links.
