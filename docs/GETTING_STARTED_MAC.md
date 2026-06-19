# Getting Started on Mac

## 1. Put the folder somewhere permanent

Recommended location:

```text
Documents/Trading-Projects/swing-rsi-self-learner
```

## 2. Open Terminal in the folder

In Finder, open the folder. Right-click the folder background and choose **New Terminal at Folder** if available.

Or open Terminal and type `cd ` with a trailing space, drag the folder into Terminal, and press Return.

## 3. Run the automatic setup

```bash
chmod +x scripts/bootstrap_mac.sh
./scripts/bootstrap_mac.sh
```

The script creates an isolated `.venv`, installs the project, and runs tests.

## 4. Activate the project when returning later

```bash
source .venv/bin/activate
```

Your Terminal prompt should begin with `(.venv)`.

## 5. Run the demo

```bash
python -m swing_rsi.cli demo
```

Synthetic data proves only that the software runs. Do not evaluate trading accuracy from it.

## 6. Open in Codex or VS Code

Open the **entire folder**, not an individual Python file. Codex must read `AGENTS.md` before editing.

## 7. Stop the environment

```bash
deactivate
```
