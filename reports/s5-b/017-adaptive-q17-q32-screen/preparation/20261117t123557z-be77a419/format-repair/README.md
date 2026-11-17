# Repair the stopped adaptive screening publication

The original campaign's repository-record check and 369-file documentation check passed. The last staged whitespace check rejected a single extra blank line at the end of publication.py. Nothing was committed, pushed or simulated. The status `applied` and `No run to stop` are consistent with that stop.

This repair removes only the extra EOF blank line from the extracted original package and its staged handover copy. It proves the Python syntax tree is unchanged, verifies all other original payloads byte-for-byte, updates the nested manifests and preparation record, and synchronizes the private publication marker. The original ZIP is preserved. Before any change, the script backs up both extracted/prepared folders, the marker and the staged patch under the publication checkout's `.git` directory.

```bash
unzip -n "$HOME/Downloads/ElectronFieldTopology-adaptive-screen-format-fix-20261118.zip" \
  -d "$HOME/Downloads"

repair="$HOME/Downloads/ElectronFieldTopology-adaptive-screen-format-fix-20261118"
package="$HOME/Downloads/ElectronFieldTopology-adaptive-Q17-Q32-screen-20261117"
backend="auto"

(
  set -euo pipefail
  bash "$repair/RUN.sh" verify
  bash "$repair/RUN.sh" run
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" install
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" preflight --backend "$backend"
  bash "$package/RUN.sh" run --backend "$backend"
  bash "$package/RUN.sh" status
)
```

The repair runs no network command, reset, solver or benchmark. Repeated repair calls verify the completed correction rather than modifying it again. Interrupted corrections can resume from their saved backup. The original `install` command reruns the actual repository record, documentation and whitespace checks before any commit. CPU/GPU qualifications still run during the normal preflight/campaign.

Optional `--package` and `--publication` select non-default local paths. [VALIDATION.json](VALIDATION.json) records real local-Git regression checks: the original EOF failure was reproduced, the repair passed `git diff --cached --check`, nested hashes and scientific payload preservation were verified, and repeat execution made no additional changes. Actual project validators run on the zbook.
