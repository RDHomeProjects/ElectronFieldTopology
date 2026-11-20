# Policy audit bundle — read-only assessment and corrected policy

Extract the ZIP and open ASSESSMENT.html in a browser. The original campaign should remain paused.

The audit, 881 decision replays, terminal-window refits and 12 tests were completed locally. No additional zbook execution is needed merely to read or reproduce this assessment. Actual continuation requires the retained workstation fields and a separate versioned handover, which is not included here.

To reproduce only the audit using the existing frozen Python environment, after extracting this folder to Downloads:

```bash
assessment="$HOME/Downloads/ElectronFieldTopology-Q17-Q32-policy-assessment-20261120"
cd "$HOME/ElectronFieldTopology-adaptive-q-screen-20261117"
uv run --frozen --python 3.12.14 python -B "$assessment/audit.py"   --output "$HOME/Downloads/Q17-Q32-policy-replay-$(date -u +%Y%m%dT%H%M%SZ)"
uv run --frozen --python 3.12.14 python -B -m unittest discover   -s "$assessment" -p 'test_policy.py' -v
```

These commands do not run field relaxation or physical-time steps, change repository source files, or contact GitHub. Do not install corrected/policy_v2.py into the original campaign. Read the proposed continuation scope and identity requirements in ASSESSMENT.md.
