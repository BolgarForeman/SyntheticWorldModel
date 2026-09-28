# SyntheticWorldModel — Working Protocol

*v0.1 · 2026-09-28 · how the design conversation, the code conversation and Foreman work together*

## 1. Roles

| Who | Owns |
|---|---|
| **Foreman** | Every decision that changes what the world is or what a result means. Final say on merges |
| **Design conversation** (this project) | The specification, the decision log's content, the work orders, and review of what comes back against the specification |
| **Code conversation** | Implementation, tests, documentation in the code, and raising questions. It follows the repository rules file (`CLAUDE.md`) |

The two conversations never talk to each other directly. Foreman carries work orders one way and reports the other. The design conversation can also read the repository itself, once it's attached here, to review pull requests directly.

## 2. The loop

1. **Agree here.** Settle in the design conversation what the next piece is and any decisions it needs.
2. **Work order.** The design conversation drafts it (§3). Foreman confirms it, then pastes it into the code conversation.
3. **Build.** The code conversation works on a branch, opens a pull request, and ends with the fixed-format report (`CLAUDE.md` §11).
4. **Review here.** Foreman pastes the report, or the design conversation reads the pull request directly. The review checks it against the specification. Choices are ruled on, questions are answered, and decisions are logged.
5. **Merge or revise.** Foreman merges, or a short revision order goes back.

Questions that come up mid-build go to Foreman immediately. They don't wait for the report when they block the work.

## 3. Work order template

```
WORK ORDER <n> — <title>
Goal: one or two sentences.
Spec: the sections this implements (spec version).
Build: the list of what to build.
Acceptance: the tests or checks that must pass for this to be done.
Out of scope: what not to touch.
Already decided: rulings that apply, so they are not re-asked.
Open: anything the coder should expect to raise.
```

## 4. Keeping the specification and the code in step

- The structure document lives in the project. A copy in the repository (`docs/design/`) is the version the code builds against, tagged with its version.
- The repository copy is updated at phase boundaries, or when a ruling changes the specification, never mid–work order.
- Every ruling from review goes to the decision log in the repository, and to the structure document at the next update.

## 5. Definition of done for a phase

- All work orders merged, with CI passing.
- The phase's checks pass on the golden worlds.
- The TRACE entry is written.
- The version tag is cut.
- The structure document is updated with anything the phase changed.
