# Publish the reviewed evidence build

The local project is prepared for this step. **Nothing is published yet.**
The repository owner and destination URL still need to be selected.

**Current user instruction:** Upload the reviewed source to a private CounterLab
repository first. Keep the website offline. The prepared Pages build job skips
private repositories even if its manual confirmation is selected. Changing the
repository or site to public requires a later explicit instruction.

## What will become public

The reviewed application source, MIT license with third-party notices, saved
model responses, numerical records, simulated integration examples, website
snapshots and replay/source downloads. Treat hypotheses as unverified model
output. Do not publish the existing working folder or an older release ZIP
wholesale: they include private state or predate the reference distribution policy.

The new source ZIP is an allowlisted publication starting point. It excludes
credentials, personal runtime history, the full upstream numeric reference,
downloaded external algorithm code, dependencies and Git metadata. Review its
contents before uploading. Retain notices and the frozen records.

## GitHub Pages path — manual publication

1. Select an existing public repository or create one under your own account.
   Use its `main` branch for the reviewed source package. Do not copy `.env`.
2. In the repository's **Settings → Pages**, choose **GitHub Actions** as the
   publishing source. Check that the repository and chosen runner use your free
   plan; no paid service or Nebius inference is needed by this workflow.
3. Open **Actions → Publish reviewed CounterLab evidence → Run workflow** on
   `main`. Only after reviewing the release, enable `confirm_publication`.
   A push or pull request never deploys automatically. The build also requires
   the repository to be public; it cannot publish from the current private phase.
4. The workflow installs pinned dependencies, explicitly fetches the small public
   reference into its temporary runner, runs offline tests, builds both interfaces,
   and packages/audits the release. The full reference is excluded from every
   uploaded file. No Nebius secret is requested or used.
5. The deployment job publishes only `judge/site`. It receives Pages deployment
   permissions; the build job has read-only repository access. The site contains
   a **Download source & live workflow** link and eight replay downloads.
6. Use the workflow's returned deployment URL. Do not guess the final domain.
   Verify it without login in a fresh browser session and add the actual URL to
   the submission draft only after it works.

This workflow follows [GitHub's custom Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
Pages supports public repositories on GitHub Free; account-specific settings and
limits still need checking when publishing. The workflow is locally prepared and
has **not** run on GitHub/Linux yet.

## Public access check

- Open every main view and both evaluation tabs, including the source investigator.
- Ensure recorded real responses and simulated examples keep their distinct labels.
- Download the full source and a numerical replay through the public links.
- Extract the source, use the pinned Python dependencies, and start read-only
  mode. Core inspection and the live workflow do not need the full upstream file.
- For the long source-reproduction replay's complete upstream identity check,
  explicitly run `python fetch_reference.py --download` inside that replay folder.
  Then `python replay.py --seed 0` reports partial coverage; `python replay.py`
  reexecutes all ten frozen seed batches. The first step requires HTTPS; replay
  itself needs no key, Docker, network or credits.
- Keep free access stable through December 15, 2026 at noon Pacific, as required
  by the [official rules](https://nebiusglobalaihackathon.devpost.com/rules).

The static site performs recorded inspection. The full source implementation
contains the runtime Nebius Token Factory integration. Do not describe opening
the static site as a fresh inference run or a new scientific discovery.
