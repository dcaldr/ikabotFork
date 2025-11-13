# ⚠️ TEMPORARY PLANNING DOCUMENTATION ⚠️

## 🚨 IMPORTANT - DO NOT COMMIT TO MAIN BRANCH 🚨

This directory contains **TEMPORARY** working documents for analysis and planning.

**Before merging to main:**
- Archive or delete these files
- Create proper GitHub issues from the analysis
- Move any keeper documentation to appropriate locations

---

## Purpose

These documents are for:
- 📝 In-depth problem analysis before creating GitHub issues
- 🎯 Feature planning and design discussions
- 🔍 Code review findings and technical decisions
- 💭 Collaborative planning on feature branches

---

## File Naming Convention

- **`issue-XX-description.md`**: Problem analysis and bug documentation
- **`feat-XX-description.md`**: Feature proposals and design documents
- **`fix-XX-description.md`**: Minimal fixes and quick patches

---

## Current Documents

### Issues
- **issue-01-webserver-ip-detection-linux.md**: Web server local IP detection fails on Linux/Raspberry Pi platforms
- **issue-02-autopirate-bugs.md**: AutoPirate has missing null check (HIGH) + graceful recovery needs logging (MEDIUM) + feature requests
- **issue-03-background-process-restart.md**: Background processes don't restart properly - initial analysis (3 functions)
- **issue-03-background-process-restart-COMPREHENSIVE.md**: ⭐ Complete analysis of ALL 20 background functions + webServer reconnection solution
- **issue-03-session-data-reconnection.md**: Session data structure analysis + process reconnection enhancement proposal (Phase 1: parse status, Phase 2: structured processDetails)
- **issue-04-alert-missing-pirate-classification.md**: ⭐ MEDIUM - alertAttacks doesn't distinguish pirate attacks from player attacks (causes confusion)

### Features
- **feat-03-cli-table-auto-update.md**: Add auto-refresh capability to CLI process table (configurable, non-disruptive)
- **feat-04-cli-menu-map-and-flows.md**: Complete CLI menu map, user flow analysis, and missing back button identification
- **feat-05-telegram-port-feasibility.md**: Telegram bot interface port feasibility analysis and implementation plan (Difficulty: 6-7/10)
- **feat-06-telegram-plugin-implementation-plan.md**: Plugin-based Telegram interface using existing infrastructure (Difficulty: 3-4/10, NO new dependencies!)
- **feat-07-telegram-complete-separation-plan.md**: Complete separation architecture with ANSI formatting, zero core changes, ready-to-use prompt
- **feat-08-telegram-zero-coupling.md**: ⭐⭐⭐ RECOMMENDED - Terminal emulator approach, TRUE zero coupling, 290 lines, 4 days, works with ANY future changes automatically!

### Fixes
(None yet)

---

## Workflow

1. **Discovery**: Find problem or plan feature
2. **Document**: Create detailed analysis document here (issue-XX.md, feat-XX.md, etc.)
3. **Discuss**: Use these docs to discuss approach and solutions
4. **Implement**: Code the solution on feature branch
5. **GitHub Issue**: Create proper issue from analysis when ready
6. **Clean Up**: Archive/delete temp docs before merging to main

---

## Notes

- ✅ Safe to commit on feature branches for collaboration
- ✅ Safe to reference in PR discussions
- ❌ Should NOT be merged to main branch
- ❌ Not for end-user documentation (use main README.md or wiki)
- 🗑️ Delete or archive after implementation complete

Think of this as a **whiteboard** or **scratch pad** - useful during work, cleaned up when done.
