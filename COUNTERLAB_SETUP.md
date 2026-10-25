# CounterLab setup checklist

**October 25 guarded-workflow setup:** No new account, key, package, GPU download
or worker rebuild is needed. Source investigator v2 uses the existing frozen
numerical worker and adds the prediction gate in the backend.

For inspection only:

```powershell
.\.venv\Scripts\python.exe scripts\start_app.py --read-only --port 8001
```

Open **http://127.0.0.1:8001/?view=source-investigator**. The saved v2 example uses
simulated planning and verified real Docker measurements. Viewing and portable
replay need neither a key nor Docker. The server blocks all investigation starts
in this mode. The original app on port 8000 can stay open.

Normal live use requires restarting that server to load the new API and keeping
Docker Desktop running. New source starts then use v2 and retain their own
per-investigation credit consent. No live run was made or newly approved here.
The trial-stop preference is unchanged; cumulative usage remains 413,410 reported
tokens / 79 calls. V2 quality has not been measured with a real model.

162 offline tests, build, worker boundary probe, two real numerical replays and
actual HTTP export/fresh-process replay passed. Earlier statuses are historical.

**Latest source-investigator update:** No new account, key or worker rebuild is
needed. Restart the existing app and open **Research study → Source investigator**.
The saved simulated-planning example can be inspected and replayed without
credits. Its four actual Docker executions, full HTTP download/replay, 107 tests
and the build pass. New live source runs have their own bounded consent. No new
live inference was used; cumulative reported usage stays 312,110 tokens / 52 calls.
The newly frozen eight-task evaluation has not run and needs its isolated
environment prepared before requesting a live batch.

**Source reconstruction update:** No additional account setup is needed. The
local worker was rebuilt and verified with the frozen source action. Restart
the app, then open **Research study → Source reproduction**. Three published
aggregates match at the original selected scale; full replay, 92 tests and the
build pass. No credits were used. Cumulative reported inference remains 312,110
tokens across 52 requests; the current account balance has not been rechecked.

**Reporting update:** No new account or NVIDIA setup is required. Version 5 uses
two planning calls at most and no reporting call. Restart the server to load it.
All 92 tests, the build and real Docker/report-export checks with simulated
planning pass. No new credits were used; cumulative reported inference remains
312,110 tokens across 52 calls. Live version-5 behavior remains untested.

**Current update, October 24:** Setup, local app, Docker worker, source study, independent validator and frozen eight-task benchmark are implemented. All 92 tests and the interface build pass. The approved benchmark used 36/40 calls with no retries. Adaptive found 2/2 available differences but only 3/8 fully correct scoped findings; simple baselines also found 2/2. No repeat setup or inference check is needed. Restart the app and inspect **Evaluation**; viewing or replaying it uses no credits. Full external parity, reliable autonomous conclusions and judging deployment remain open. See [APP_GUIDE](APP_GUIDE.md). Earlier dated status is historical.


**Updated October 24, 2026.** Project folder: `C:\MY_PROJECTS\NVIDIAxNEBIUS`.

**Current status:** Both promotional grants were redeemed; latest observed balance predates recent inference. Cumulative reported inference is 312,110 tokens across 52 calls, including the 240,279-token approved benchmark. Stop-after-trial remains saved. No further model batch is authorized by this result. Post-trial judging access remains unresolved; see [README](README.md).

The official submission deadline is **October 30, 2026, 10 a.m. PDT / 1 p.m. EDT**. Our target remains October 29. The older delivery calendar began October 16; its 42-hour allocation is historical. At three hours daily, October 21–29 provides approximately 27 hours. Prioritize access and the first scientifically valid investigation before interface expansion. [Official rules](https://nebiusglobalaihackathon.devpost.com/rules).

## 1. What is already installed

### Spending instruction from the user — October 21

All service use must be for CounterLab's hackathon work. No unrelated subscription, paid add-on, GPU rental, manual paid top-up, or paid deployment is authorized. No cash budget has been specified, so plan against confirmed promotional credits only until the user approves a specific paid amount. The observed trial-stop option states the card is never charged and access stops at trial end. The user confirms selecting Stop and saving; do not ask again. An application limit is not a provider guarantee. Trial stopping with deposited promo credit, and access through judging, still need verification before deployment. Do not advise that a billing threshold, alert, card removal, or bank block cancels incurred charges.

| Tool | Observed result | Action |
| --- | --- | --- |
| Git | 2.53.0.windows.2 | Available for source control |
| Python | 3.13.5; only 3.13 listed by the launcher | Use an isolated project environment; verify the selected adapter's dependencies before adding another Python version |
| Node.js | 22.16.0 | Available for the React/TypeScript frontend; pin compatible project dependencies |
| npm | 10.9.2 | Available; npm.cmd works in PowerShell |
| Docker | Client/Server 29.1.2; Desktop 4.54.0; Linux mode | Engine check passed in user-supplied output; actual experiment worker not yet built/tested |
| WSL | Executable present; distribution query returned access denied | Distribution/configuration not verified from this environment; do not infer that WSL is missing |
| uv | Not found on PATH | Optional; standard Python virtual environments and pip are sufficient initially |
| Storage | Approximately 328 GiB free on C: | Adequate for the initial application; estimate any later model/data downloads first |

The workspace contains planning documents, setup verification, independently written paging experiments, the bounded model/tool workflow, a private `.env`, a Python environment, and a Git repository. Token Factory access and the first $25 grant are confirmed. Offline experiments and the first live investigator comparison have run; the UI and deployed product remain to be built.

## 2. User account steps, in order

### A. Join the hackathon

1. Sign in or create an account on [Devpost](https://nebiusglobalaihackathon.devpost.com/).
2. Click **Join Hackathon** and confirm the joined state.
3. Check personal eligibility, including age of majority and organizer/judge conflicts.

Our planned track is **Best Apps and Agents**. It calls for Nemotron on Nebius Token Factory. Nebius AI Cloud deployment is encouraged but not required for that track. [Rules](https://nebiusglobalaihackathon.devpost.com/rules).

### B. Create Token Factory access

1. Open [Nebius Token Factory](https://tokenfactory.nebius.com/) and sign in using the available Google or GitHub option.
2. Use the same email consistently for credit claims where the forms require matching account details.
3. Complete billing onboarding if proceeding: the current [billing documentation](https://docs.tokenfactory.nebius.com/other-capabilities/billing-new) requires a bank card. The form's $0 authorization verifies the card; it does not guarantee free future usage. Review automatic charging and actual credit balance before API work. A billing threshold is a charge trigger, not a hard spending cap. No card or billing action has been performed by the assistant.

The official [quickstart](https://docs.tokenfactory.nebius.com/quickstart) documents account access and the inference endpoint. The documentation's sample models are examples; our hackathon runtime must use the NVIDIA Nemotron model we select and verify.

### C. Claim the advertised credits

1. Open the [hackathon credit form](https://nebius.com/promo-code?utm_promo_event_code=2026-devpost-global-ai-hack&utm_promo_code_type=Token_Factory&utm_promo_activation_code=NEBIUS-DEVPOST-GLOBAL26).
2. Use activation code **NEBIUS-DEVPOST-GLOBAL26** for the advertised $25 Token Factory offer.
3. Join the [Nebius Builder Program](https://dev.nebius.com/builders), verify email, and claim its advertised additional $25 Token Factory credit.
4. Confirm the credits actually appear in the account; record balance and expiration without storing payment information.

Signing into Token Factory from a general link does not establish that the event credit request has been submitted or redeemed. Use the same Token Factory account email in the request forms. `NEBIUS-DEVPOST-GLOBAL26` is the activation code requested by the event form; do not assume it is a personal billing redemption code. Follow the resulting instructions. If Nebius issues a redemption code, use balance → Top up → With promo code, then verify Transactions. Missing credits should be raised with Nebius through the [official event FAQ's support route](https://nebiusglobalaihackathon.devpost.com/details/faqs), which directs entrants to Nebius Discord. No request has been sent on the user's behalf.

The event [resources page](https://nebiusglobalaihackathon.devpost.com/resources) advertises both offers. Both $25 grants are now redeemed, with a $50 account balance confirmed by the October 24 screenshot. No repeat redemption is required. The Builder email says applied credits do not expire; separate trial-stop access still needs verification for judging. Partner offers are claimed separately using welcome-email links and are subject to their terms. These are inference credits; do not count them as a GPU-compute or hosting budget.

### D. Create and store a project API key

1. In Token Factory, open **API keys** and create a key named `counterlab-dev`.
2. Copy [.env.example](.env.example) to `.env` in the project folder.
3. Paste the key locally after `NEBIUS_API_KEY=`. Never send it in chat, screenshots, public repositories, frontend code, or feedback logs.
4. In Token Factory's model catalog/playground, select an NVIDIA Nemotron model available to the account. Copy its exact model ID into `NEBIUS_MODEL=`. We will verify its tool/JSON behavior before freezing the choice.
5. Keep `NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/` unless an official account-specific endpoint requires otherwise.

The [.gitignore](.gitignore) excludes local environment files and keeps the empty example tracked. No real `.env` or key has been created by this setup document. Nebius documents key creation and one-time key display in its [API authentication guide](https://docs.tokenfactory.nebius.com/api-reference/introduction).

### E. Have source-control access ready

Use an existing [GitHub account](https://github.com/) or create one. Repository initialization, structure, licensing, and publication belong to the build workflow. A public licensed source repository is required for submission. Do not create or share a broad personal access token merely to complete this checklist.

## 3. Local work the assistant can handle during the build

- Initialize source control and verify that local credentials are excluded.
- Create the Python environment, backend, React/TypeScript frontend, and compatible pinned dependencies.
- Run a small genuine Nemotron API smoke test with the key kept local; record model ID, response, tokens, and errors without logging the key.
- Confirm tool calling and structured output on a real planning task.
- Validate a faithful experimental adapter and reproducible paired run before building the full interface.
- Add container worker isolation and verify Docker access before executing experiments in the hosted product.
- Establish a deployment path that remains usable during judging, with its costs reviewed before provisioning paid resources.

No separate OpenAI API key is required for calling Nebius's compatible endpoint. Large model downloads, local Nemotron installation, CUDA Toolkit installation, GR00T/Isaac, and a GPU rental are not prerequisites for the initial API/backend/paging work. Add experiment-specific GPU dependencies only if the chosen investigation requires them.

## 4. Accounts and tools that can wait

| Item | When needed |
| --- | --- |
| Hugging Face account/token | Only if selected artifacts require authenticated or gated access; public files may not require it |
| Tavily account/key | Optional later search integration, only after it serves a useful investigation step |
| Nebius AI Cloud capacity | If experiments or deployment justify it; separate from Token Factory inference access |
| Hosting provider account | When selecting the working judged deployment; no provider selected yet |
| YouTube channel/upload access | Before recording and uploading the required public demo video; do not leave verification to the final day |
| Extra agent frameworks or observability services | Only after a concrete requirement justifies them |

## 5. Ready-to-build checkpoint

- [x] Devpost joined status confirmed directly by the user.
- [x] Token Factory login works.
- [x] First $25 promotional balance confirmed; billing policy reviewed separately.
- [x] Project key stored in local `.env`, ignored by Git, and authenticated model-catalog request successful.
- [x] Accessible setup model `nvidia/Nemotron-3_5-Lightning` verified through actual responses; final investigator selection remains a build task.
- [x] GitHub account available, confirmed directly by the user; publication authentication is a later task.
- [x] First successful inference recorded from the user's connection-probe output.
- [x] Synthetic forced-tool/structured-output round trip passed; reported by the user October 21.
- [ ] Final investigator model selected through task-specific comparison; autonomous scientific tool selection remains to be evaluated.

Report completion using account/status information only, such as “Devpost joined; Token Factory accessible; credits visible; key saved locally.” API keys and passwords are never needed in the message.

## 6. Step-by-step local setup, performed by the user

Git, Python 3.13.5, Node 22.16.0, npm 10.9.2, and VS Code are present. The installed Node version meets Vite's published general minimum; individual dependencies still need compatibility checks. [Vite requirements](https://vite.dev/guide/).

### Step 1 — Open the correct workspace

In VS Code, choose **File → Open Folder** and select `C:\MY_PROJECTS\NVIDIAxNEBIUS`. The Explorer should show `COUNTERLAB_PRD.md` and `.env.example`. Choose **Terminal → New Terminal**, using PowerShell.

Set the terminal's working folder explicitly:

```powershell
Set-Location -LiteralPath 'C:\MY_PROJECTS\NVIDIAxNEBIUS'
```

### Step 2 — Create and save the Nebius key

In the existing Token Factory account, choose **API keys → Create API key**. Name it `counterlab-dev`, and save the displayed value locally. Nebius documents one-time key display in its [authentication guide](https://docs.tokenfactory.nebius.com/api-reference/introduction).

In VS Code's Explorer, duplicate `.env.example` and name the copy exactly `.env`. If `.env` already exists, edit it rather than replacing it. Enter the key after `NEBIUS_API_KEY=` and save. Keep the provided `NEBIUS_BASE_URL` unchanged. Leave `NEBIUS_MODEL` blank until we verify a suitable Nemotron model against the actual account.

Expected result: a local `.env` with the key, saved without exposing its contents in chat or screenshots. A blank model field is intentional at this stage.

### Step 3 — Create the project's Python environment

Run these commands from the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
```

Expected result: Python 3.13.5, and pip located under the project's `.venv`. Use this interpreter for CounterLab; dependencies will be installed and pinned as the application is created. Environment activation is optional: the explicit interpreter path works without changing PowerShell execution policy. [Python virtual environment documentation](https://docs.python.org/3.13/library/venv.html).

In VS Code, open the command palette, choose **Python: Select Interpreter**, then select `.venv\Scripts\python.exe`. If that command is unavailable, the Microsoft Python extension is optional editor support; the terminal commands above still work.

### Step 4 — Initialize source control and verify the key exclusion

The latest check found no Git repository here. Run:

```powershell
git init -b main
git check-ignore .env
git status --short
```

Expected result: `git check-ignore .env` prints `.env`. Git status may list `.env.example`, which contains no key, but must not list `.env`. If `.env` appears, fix the ignore configuration before staging anything. First commits and GitHub publication follow after we review the project files.

### Step 5 — Start Docker Desktop and verify Linux containers

Open **Docker Desktop** from the Start menu and wait for the engine to be ready. Then run:

```powershell
docker version
docker info --format '{{.OSType}}'
```

Expected result: both **Client** and **Server** sections from the first command, and `linux` from the second. A client version alone does not prove the engine works. If Docker reports a WSL or virtualization error, preserve the exact error so we can address that cause. Do not reinstall or reset Docker as a generic troubleshooting step. [Official Windows setup](https://docs.docker.com/desktop/setup/install/windows-install/).

Docker is needed before validating isolated experiment workers. Its absence does not prevent preparing the API or running our own reviewed local development checks. A separate Docker account is not needed to report these engine checks.

### Step 6 — Confirm account access and billing controls

Devpost membership and GitHub account availability are confirmed by the user; no further inspection is needed. GitHub repository authentication will be handled when publication is required. Remote hosting, model-weight downloads, Tavily, and extra paid services can be decided after the first valid investigation works.

The user has supplied the actual **Paid usage after trial** choices and now confirms selecting **Stop usage when the trial ends**, then **Save preference**. This step is complete; no repeat is needed. The dialog says the card is never charged and projects/API keys stop working at trial end. It does not establish whether deposited promo credit extends trial access. Resolve that and the December 15 judge-access requirement before deployment; do not enable paid continuation automatically to fix a blocked request.

### Step 7 — Verification together

Report these non-secret statuses:

- Key saved in `.env`.
- Python environment created and its version commands succeeded.
- Git initialized and `.env` ignored.
- Docker engine works with Linux containers, or the exact error it returns.
- Devpost joined; GitHub account available.
- The actual paid-usage setting/options, without card details.

Then we verify a short genuine Nemotron request and its structured-output/tool behavior using the confirmed balance and bounded request settings. We also check that we can obtain and implement the first experiment faithfully. Successful local setup alone is not proof that this scientific investigation is feasible.

The prepared connection checker runs without installing packages. Its default invocation is local only:

```powershell
.\.venv\Scripts\python.exe scripts\check_nebius.py
```

After saving the Stop preference, this explicit command sends one short request to an account-listed candidate, capped at 256 output tokens with no automatic retries:

```powershell
.\.venv\Scripts\python.exe scripts\check_nebius.py --probe --model 'nvidia/Nemotron-3_5-Lightning'
```

Lightning is an initial connection-test candidate, not the final quality/cost decision. The output contains model IDs, check status, and token counts; it does not print the key or raw model text. A passed connection probe does not yet validate structured output, tool execution, or scientific correctness.

**Connection probe completed October 21:** The user's output records `probe_passed`, exact requested/returned ID `nvidia/Nemotron-3_5-Lightning`, expected text, and finish reason `stop`. Usage was 26 prompt + 235 completion = 261 total tokens. No repeat of that probe is needed.

The synthetic integration check uses a predefined latency fixture. It forces one allowlisted tool call, validates its JSON arguments, computes the fixture means in local Python, sends that evidence back, and checks the model's schema-constrained JSON answer against those values. It executes no model-generated code or arbitrary paths. This checks the tool protocol, output shape, and simple evidence use; it does not establish autonomous experiment selection or scientific validity. The request format follows Nebius's [tool-calling](https://docs.tokenfactory.nebius.com/ai-models-inference/function-calling) and [structured-output](https://docs.tokenfactory.nebius.com/ai-models-inference/json) documentation. The user has now verified this path on Lightning.

After saving the Stop preference, run:

```powershell
.\.venv\Scripts\python.exe scripts\check_nebius.py --tool-probe --model 'nvidia/Nemotron-3_5-Lightning'
```

This makes **at most two requests**, each capped at **1,024 output tokens**, with no automatic retries. It reports safe validation flags, elapsed time, and usage; the expected overall status is `tool_probe_passed`. A failure stops the check; do not repeatedly rerun or enable paid continuation to fix access. The assistant has not made these live requests. The final investigator selection will compare Nemotron 3 Ultra and Nemotron 3.5 Super VL on CounterLab tasks; this setup fixture does not choose a winner.

**Tool probe completed October 21:** The user's result is `tool_probe_passed`, with both returned IDs matching Lightning and every argument, execution, structured-output, and evidence flag true. Usage was 707 prompt + 642 completion = 1,349 tokens in two requests; total elapsed time was 3.797 seconds. The Stop preference is also confirmed saved. Both setup probes are complete and need no repeat. Basic development/live integration prerequisites are ready; implement the first real adapter next. Builder approval, hosting, and extra service accounts are not prerequisites for that local build.

**Ready to develop** means the workspace, isolated Python environment, secret handling, and local source control work. **Ready for live integration** additionally requires a working model request and reviewed billing controls. **Ready for isolated experiment execution** additionally requires the Docker worker check. These are separate observable milestones, not extra accounts to purchase.

## 7. NVIDIA Nemotron, NVIDIA NIM, and npm are different

For the planned integration, CounterLab sends requests to **Nebius Token Factory**, authenticated with a **Nebius API key**, and selects an **NVIDIA Nemotron model** hosted there. This is the Best Apps and Agents track's specified integration. A separate NVIDIA-hosted inference account/key or a local Nemotron installation is not part of this path. [Hackathon rules](https://nebiusglobalaihackathon.devpost.com/rules), [Nebius authentication](https://docs.tokenfactory.nebius.com/api-reference/introduction).

| Credential or name | Meaning | Role in this setup |
| --- | --- | --- |
| npm access token | Authenticates package-registry operations | Does not authorize model inference; our initial public frontend dependencies do not require a personal npm token |
| NVIDIA NIM / NVIDIA API key | Authorizes the relevant NVIDIA-hosted model service | Different provider route; does not replace the Nebius key |
| Nebius Token Factory API key | Authorizes requests to Nebius's inference API | Required credential for CounterLab's planned Nemotron use |
| NVIDIA Nemotron | The model family being called | Select an accessible exact model ID and verify real responses |

Primary references: [npm tokens](https://docs.npmjs.com/about-access-tokens/), [NVIDIA-hosted inference authentication](https://docs.nvidia.com/nemo/retriever/latest/extraction/api-keys/).

The NVIDIA integration is now verified for Lightning's connection and synthetic forced-tool/structured-output path. The final investigator model and autonomous scientific tool use still require task-specific evaluation. For this remote-inference path, CUDA Toolkit, NIM containers, NeMo, and Isaac are not prerequisites. GPU libraries are a separate later decision if a scientific experiment needs them. No stored npm or NVIDIA keys have been inspected or identified by this clarification.
