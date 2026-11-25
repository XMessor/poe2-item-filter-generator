# Profiles

Your own settings live here, one folder per profile, e.g. `profiles/my_profile/`. A profile holds
only the files and values you change; everything else comes from [`config/`](../config/), so
updating the repository brings you the fixes without touching your settings.

Nothing in this folder except this README is part of the repository: your profiles stay on your
computer.

```powershell
python -E -s -m engine.config --profile profiles/my_profile    # check
python -E -s -m engine.build  --profile profiles/my_profile    # -> profiles/my_profile/filters/
```

- By hand: the [Customization Guide](../.docs/customization_guide.md).
- With an AI agent: [`AGENT_GUIDE.md`](../AGENT_GUIDE.md).
