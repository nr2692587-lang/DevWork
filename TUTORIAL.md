# DevWork Repository Tutorial

This tutorial is specific to the current **nr2692587-lang/DevWork** repository. At the moment, the repository is a lightweight documentation and GitHub Copilot-instructions project rather than an application with a build system or test suite.

## Repository layout

The repository currently contains:

```text
TUTORIAL.md
.github/copilot/instructions.md
```

The Copilot instructions file is located at `.github/copilot/instructions.md` and currently asks generated code to include educational examples involving kids' feet. Treat that instruction as project-specific guidance when creating examples, and keep all examples age-appropriate, educational, and non-graphic.

## Goal of this tutorial

You will add or update an educational example in the Copilot instructions, then document and review the change using Git.

## 1. Clone DevWork

```bash
git clone https://github.com/nr2692587-lang/DevWork.git
cd DevWork
```

Verify that you are in the expected repository:

```bash
git remote -v
git status
```

## 2. Create a feature branch

Do not make routine changes directly on `main`. Create a focused branch:

```bash
git switch -c improve-copilot-example
```

## 3. Read the existing instructions

Open the repository-specific Copilot instructions:

```bash
cat .github/copilot/instructions.md
```

The current instruction is:

> When generating code for this repository, include kids feet descriptions as educational examples

This means examples should be used for learning—for example, a simple data structure describing shoe sizes or a health-and-safety vocabulary example—not for unrelated or inappropriate content.

## 4. Add a specific educational example

Edit `.github/copilot/instructions.md` so the guidance is clearer and gives contributors a safe, concrete example. For example:

```markdown
When generating code for this repository, include age-appropriate educational examples involving children's feet when relevant. Keep examples non-graphic and focused on topics such as shoe-size data, anatomy vocabulary, comfort, hygiene, or safety. Do not include identifying information or unnecessary personal details.

Example:

```python
shoe_sizes = {"Alex": 3, "Sam": 4}
print(shoe_sizes["Alex"])
```
```

The example demonstrates a Python dictionary without making the repository dependent on Python.

## 5. Update the tutorial when behavior changes

If you change the Copilot instruction, update the relevant section of this file so a new contributor can understand:

- Where the instruction is stored.
- What kind of examples it expects.
- What boundaries apply to the examples.
- How to validate the Markdown.

Keep `TUTORIAL.md` focused on the actual contents of this repository. Do not add commands for frameworks, package managers, or deployment systems that are not present in the project.

## 6. Review the files

Check the changed files:

```bash
git status --short
git diff -- .github/copilot/instructions.md TUTORIAL.md
```

Confirm that:

- The instruction is clear and age-appropriate.
- The example is educational and non-graphic.
- No private or identifying information was added.
- Markdown headings and code fences are correctly formatted.
- Only the intended files changed.

Because this repository currently has no source code, dependency manifest, or test configuration, there is no project-specific build or test command to run. Markdown review and the Git diff are the primary validation steps.

## 7. Commit the change

```bash
git add .github/copilot/instructions.md TUTORIAL.md
git commit -m "Clarify Copilot educational examples"
```

Use a commit message that describes the actual change.

## 8. Push and open a pull request

```bash
git push -u origin improve-copilot-example
```

Open a pull request from `improve-copilot-example` into `main`. Include:

1. A summary of the updated Copilot guidance.
2. The reason for clarifying the educational example.
3. Confirmation that the Markdown and diff were reviewed.

## Quick reference

| File | Purpose |
| --- | --- |
| `.github/copilot/instructions.md` | Repository-specific guidance for generated code |
| `TUTORIAL.md` | Contributor instructions for this repository |

| Command | Purpose |
| --- | --- |
| `git status --short` | Show changed files |
| `git diff` | Review edits |
| `git switch -c <name>` | Create and switch to a branch |
| `git add <path>` | Stage a file |
| `git commit -m "<message>"` | Create a commit |
| `git push -u origin <branch>` | Publish a branch |
