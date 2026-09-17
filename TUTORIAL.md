# DevWork Tutorial

Welcome to **DevWork**! This tutorial explains how to get started with the repository and make a small change safely.

## 1. Clone the repository

```bash
git clone https://github.com/nr2692587-lang/DevWork.git
cd DevWork
```

## 2. Create a working branch

Create a separate branch for your changes instead of working directly on `main`:

```bash
git checkout -b my-change
```

Choose a descriptive branch name, such as `add-tutorial` or `fix-readme`.

## 3. Explore the project

List the files in the repository and inspect the existing documentation:

```bash
ls
find . -maxdepth 2 -type f | sort
```

Look for the project's README, source files, tests, and configuration files. Read the existing documentation before making changes.

## 4. Make a change

Edit or add the files needed for your task. Keep changes focused and follow the conventions already used in the repository.

For documentation changes, use clear headings, short paragraphs, and code blocks where helpful.

## 5. Review your changes

Check which files changed and inspect the diff:

```bash
git status
git diff
```

Before committing, confirm that:

- The change solves the intended problem.
- No unrelated files were modified.
- Documentation and code examples are accurate.
- Tests or validation commands pass when applicable.

## 6. Commit your work

Create a concise commit with a descriptive message:

```bash
git add .
git commit -m "Add project tutorial"
```

## 7. Push the branch

```bash
git push -u origin my-change
```

## 8. Open a pull request

On GitHub, open a pull request from your branch into `main`. In the description, explain:

1. What you changed.
2. Why you changed it.
3. How you tested or reviewed it.

Keep the pull request focused so it is easy to review.

## Useful Git commands

| Command | Purpose |
| --- | --- |
| `git status` | Show the current working-tree status |
| `git log --oneline` | View recent commits |
| `git diff` | Review uncommitted changes |
| `git branch` | List local branches |
| `git switch main` | Switch to the `main` branch |
| `git pull` | Download and integrate the latest changes |

## Next steps

Use this workflow for future contributions to DevWork. As the project grows, expand this tutorial with project-specific setup instructions, testing commands, and deployment guidance.
