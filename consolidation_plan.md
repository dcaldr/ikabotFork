# Git Branch Consolidation & Renaming Plan

## Goal
Consolidate features for local use while **renaming and preserving** feature branches for potential future merging with the original project.

## 1. Rename Feature Branches
We will rename the "messy" Claude branch names to clean, descriptive names.

### Telegram Plugin
*   **Old**: `origin/claude/fix-telegram-plugin-017h3EHYhNmjw1bKpnadu4JC`
*   **New**: `telegram-plugin-ikachef`
*   **Command**:
    ```powershell
    git checkout claude/fix-telegram-plugin-017h3EHYhNmjw1bKpnadu4JC
    git branch -m telegram-plugin-ikachef
    ```

### Pirate Defense (Detection & Auto-Train)
*   **Old**: `origin/claude/auto-train-defense-01B2FzQ1cMSE1xLwvcXrRM1b`
*   **New**: `pirate-detection-auto-response`
*   **Description**: This feature includes both **Pirate Attack Detection** (alerting) and **Auto-Response** (converting crew to defend).
*   **Command**:
    ```powershell
    git checkout claude/auto-train-defense-01B2FzQ1cMSE1xLwvcXrRM1b
    git branch -m pirate-detection-auto-response
    ```

## 2. Create Combined Branch
Create a `combined` branch for your daily use, merging these clean branches.

```powershell
# Start from master
git checkout master
git pull origin master
git checkout -b combined

# Merge the renamed branches
git merge pirate-detection-auto-response -m "Merge feat: Pirate Detection & Auto-Response"
git merge telegram-plugin-ikachef -m "Merge feat: Telegram Plugin (IkaChef)"
git merge origin/claude/analysis-and-documentation-011CUz15BfEZzx2rdz5LF9Mk -m "Merge docs: Analysis"
```

## 3. Cleanup (Archive Only)
We will **NOT** delete the feature branches (`telegram-plugin-ikachef`, `pirate-detection-auto-response`) so you can use them for PRs later.

We *will* archive the unused "any city" pirate feature.
```powershell
git tag archive/feat-pirate-from-any-city origin/claude/feat-pirate-from-any-city-011CV3zADf5EVTx1MtbZiBk7
```
