# Plan reviewer

This is the take-home assignment for the Artificial Intelligence Engineer role at WhiteSpace. It is sized for about two hours of work, deployment included, and you have one day to hand it in. Tell us in your note how long you spent. We would rather see good choices than more hours.

## The story

A town council's events officer approves the plans that volunteer committees send in for local events. Each plan is a few pages: goals, tasks, who does what, what depends on what, and a target date. She has to judge whether a plan is complete, consistent and achievable by its date. Her email to us is in [docs/client-email.md](docs/client-email.md).

## What you get

A small app that reviews a plan in three steps: a model reads it and lists its tasks and findings, code schedules the tasks, and a page shows the result. It works, but it does everything badly.

The three sample plans are in `data/plans/`. The page shows their stored reviews from `data/reviews/`, so the app runs without an API key. The backend is FastAPI; the frontend is React. The page's **Review with AI** button generates, checks and saves a fresh review using your configured provider, then immediately updates the schedule. Normal page loads use the saved result without another model call.

**Edit review** lets you correct the deadline, task names, people, durations and
dependencies, and dismiss remarks. **Apply and recalculate** updates the schedule
without calling AI. Corrections stay in the current view until you switch plans,
reload, restore the AI review, or run a new review. They do not overwrite the
model-generated files in `data/reviews/`.

## Run it

You need Python 3.11 or newer, Node 20 or newer, and make. On Debian or Ubuntu, `python3 -m venv` also needs the `python3-venv` package. Docker is optional.

Each `make` target is shown with the commands it runs, if you would rather run them by hand. Run each line on its own, starting from this folder.

`make setup`:

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm install
```

`make run` builds the page and serves it at http://localhost:8000:

```sh
cd frontend && npm run build
cd backend && ../.venv/bin/uvicorn app.main:app --port 8000
```

On Windows PowerShell, run these equivalents from this folder. The first
setup is needed once; rebuild the frontend when its code changes, and start
the final command whenever you want to run the website.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm install
npm run build
cd ..\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

`make test`:

```sh
.venv/bin/pytest backend/tests
```

The review command uses LangChain with OpenAI by default. Copy `.env.example`
to `.env` in this folder and fill in `OPENAI_API_KEY`. The command loads this
file automatically; existing environment variables take precedence. `.env`
is excluded from Git and the Docker build.

`REVIEW_PROVIDER` selects `openai` or `anthropic`. `REVIEW_MODEL` selects the
model; if left empty, it defaults to `gpt-5.4-mini` for OpenAI or
`claude-sonnet-4-6` for Anthropic. To switch to Anthropic, change both settings
and fill in `ANTHROPIC_API_KEY`. Use a model that supports native structured
output. No LangSmith account or key is needed.

The default OpenAI model uses medium reasoning effort to check the whole plan.
For another OpenAI reasoning model, `REVIEW_REASONING_EFFORT` can be set
explicitly; omit it for models that do not support reasoning effort.

Run from this folder:

```sh
mkdir -p out
./review data/plans/spring-market.md out/spring-market.json
```

On Windows PowerShell, use this equivalent after setup:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m app.review data/plans/spring-market.md out/spring-market.json
```

The command sends the full document to the selected provider with a dedicated
review prompt and a structured JSON response format. It writes UTF-8 JSON and
exits with a non-zero status on an API, file or validation error. Code checks
the response fields, task ids and dependencies, and checks every non-null
quote against the source after normalising whitespace. A rejected answer
gets one correction attempt, then fails without replacing the saved review.
Opening a plan in the page uses its stored review; the command updates it
when `data/reviews/<plan-id>.json` is passed as the output. The page's
**Review with AI** button also saves the new result automatically.

The scheduler respects dependencies and prevents overlapping tasks for the
same person. Circular dependencies are shown without attempting to schedule
them. OR-Tools CP-SAT searches for the shortest finish with a six-second
solver limit. A valid fallback is always available; the response and page
state whether the shortest finish was proved, rather than presenting an
unproven result as optimal. An unclear review deadline stays unknown.

The `Dockerfile` builds one container that serves the page and the API on `$PORT`, 8000 by default.

## What we ask

You may change anything, the stack included, as long as the two contracts hold. A good result does this for the events officer:

- **AI.** She can trust the review: it always has the fixed format, and every quote is word for word from the plan. The model proposes and your code decides: an unusable answer is caught and reported, never shown as if it were right.
- **Algorithm.** Any method or library is fine, solvers included. She learns the earliest day the plan can really finish, given its dependencies and that one person does one task at a time, and whether that meets the deadline. Tasks that wait on each other in a circle are named. Show us why we should believe the answer.
- **Backend.** Both contracts hold, bad input gets a clear refusal, and tests show it. Someone else can clone the repo, follow this README and run it.
- **UX.** She opens a plan and sees within seconds whether it can make its date and what is wrong. She can check where each remark comes from in the plan, correct the review when she disagrees, and see what changes. Use `BRAND.md` for the look.

There is more here than fits in two hours. Decide what matters most to her, and say in the note what you cut.

## Rules we check by script

The schedule endpoint and the review command follow two fixed contracts, written out with examples in [docs/contracts.md](docs/contracts.md). In short: at most 60 tasks per request, an answer within 10 seconds, and every quote word for word in the plan. Check your output with:

```sh
python3 check_contract.py schedule <base_url>
python3 check_contract.py review <file.json>
```

This checks the shape and the scheduling rules. It does not check quotes against the plan, or whether your schedule is the shortest. We post our own task lists to your endpoint and compare your end day with the best we know. We run your review command on plans you have not seen. We run `./review` with up to 300 seconds per plan and, if your URL fails, we check your `Dockerfile` with `PORT=8000`.

## Models and AI tools

- Use any model with your own key, live from the app or offline. Your choice; tell us why in the note.
- No key? OpenRouter has a free model you can use, also for AI features in the app: [nvidia/nemotron-3.5-super-vl:free](https://openrouter.ai/nvidia/nemotron-3.5-super-vl:free). A free OpenRouter account is enough. This version supports OpenAI and Anthropic; using OpenRouter would require another provider integration.
- Keep your review outputs for the three sample plans in `data/reviews/`, under the same file names. They are what your `./review` wrote, not edited by hand.
- Name the environment variables your review command needs in the note. If we cannot run your model, we judge the AI part on your code and those outputs.
- How the page uses AI is up to you. We judge it on whether it helps her decide.
- AI coding tools are allowed and expected. Say in the note how you used them and how you checked what they wrote.

## Hand in

You received a zip, so start with `git init` in this folder, commit the starter as it is, then commit as you go; we read the history. Reply to our email with:

1. A link to a git repo we can clone. If it is private, invite both accounts named in the email this zip came with.
2. The URL of your deployed app. Any host works, free tiers included; our script allows a slow first answer from a sleeping host. Keep the URL up for 14 days after you hand in.
3. `NOTES.md`, filled in, in the repo. The note is your chance to explain your choices. Keep it to one page.
