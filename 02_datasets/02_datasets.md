# Step 02 — Datasets: UI Checklist

**Docs:** [Manage datasets](https://www.comet.com/docs/opik/evaluation/manage_datasets/)

Run `python 02_datasets.py`, then verify in Opik UI > Datasets > elastic-agent-qa-v1.

- [ ] Dataset `elastic-agent-qa-v1` is listed under Datasets
- [ ] At least 2 distinct versions are visible in the version history
- [ ] Current version contains 6 items
- [ ] First item's expected output ends with `"You can also specify mappings in the same request."`

Proceed to `03_metrics.py`.

---

**Running via the ZenML pipeline?** The dataset registration logic also runs as the first step of the ZenML pipeline (`register_dataset_step`), but with one deliberate difference: the pipeline is idempotent — it inserts / updates / skips rows without churning dataset versions on every rerun. This standalone script is the one that demonstrates versioning. See the **Run via ZenML** section in the top-level `README.md`.
