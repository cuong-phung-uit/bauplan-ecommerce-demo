# Project: Bauplan agent demo (university presentation)

Purpose: demo of an AI agent debugging and fixing a broken Bauplan pipeline, following the
"debug and fix with Claude Code + Bauplan" workflow. Audience: Advanced Database Systems class.

## Environment
- Bauplan username: cuong-phung-uit. Confirm with `bauplan info`.
- Demo data branch: cuong-phung-uit.ecommerce-pipeline
- Project folder: /Users/cuongphung/Projects/csdltt/bauplan/bauplan_ecommerce (Git repo)
- Bauplan project to run: pipeline/ (use `bauplan run --project-dir pipeline`)
- Use the Bauplan skills plugin (bauplan@bauplan-skills): bauplan-data-pipeline to build,
  bauplan-debug-and-fix-pipeline to debug.

## Hard rules
1. NEVER run, write, merge or delete anything on Bauplan `main`. It is shared with other users.
   Reading from main (e.g. `--from-ref main`) is allowed.
2. Always create branches with an explicit `--from-ref`. The CLI's active branch may point to a
   deleted branch.
3. Never guess CLI flags: check `bauplan <command> --help` first. There is no `bauplan run --id`.
4. Every code change goes through a Git commit with a clear message.
5. Do not delete Bauplan branches or Git branches unless I ask.
6. When you give me shell commands, give real values, never <placeholders> (I use zsh).