# Notes

Live app: https://whitespace-dz25.onrender.com/

## Time spent

About 1 hour 50 minutes, including setup and deployment.

## What I did

- Connected OpenAI through LangChain to read plans. I chose `gpt-5.4-mini` for its cost and JSON output support, using my own key.
- Added checks for the answer format, task references and exact quotes. Invalid answers are corrected once or rejected.
- Fixed scheduling with OR-Tools: one job per person at a time, dependencies respected, and circular dependencies reported.
- Made the result clear on the page. Added source quotes, editing and recalculation.
- Generated the three sample reviews with AI and deployed the app on Render.

## What I cut and why

- Editing is limited to existing tasks. I did not add saved edits or task creation/deletion, to keep the editing feature small. Corrections reset when you reload or switch plans.
- The scheduler stops searching after six seconds so it can answer within ten seconds. It may return a valid schedule without proving it is the shortest; the page makes that clear.

## What is not ready

Manual edits reset when you reload or switch plans. You can change existing tasks, but cannot add or delete tasks yet.

## What I would do next and a rough estimate

Save manual edits in the browser so they survive a reload. Rough estimate: 20-30 minutes, including checking that restoring the original AI review still works.

## How I used AI tools

Codex helped write and debug the code and prompt. Checked the work with 31 tests, comparisons against the original plans, browser checks and the supplied contract checker. Small schedules were also compared with every possible order of each person's tasks. The deployed schedule endpoint passed the checker.

## Environment variables my review command needs

- OpenAI: `OPENAI_API_KEY`.
- Optional settings: `REVIEW_PROVIDER`, `REVIEW_MODEL`, `REVIEW_REASONING_EFFORT`. Defaults are `openai`, `gpt-5.4-mini` and `medium`.
- For Anthropic: set `REVIEW_PROVIDER=anthropic`, add `ANTHROPIC_API_KEY` and use an Anthropic `REVIEW_MODEL` (default `claude-sonnet-4-6`).

Settings can go in `.env`. Keys are excluded from Git.
