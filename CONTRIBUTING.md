# Contributing

Atlas Ads Workbench is local-first. Never commit real seller data, Amazon
credentials, cookies, API keys, customer exports, or `.env` files.

Run the test suite before opening a pull request:

```bash
python3 -m unittest discover -s tests -v
```

Keep changes narrow, add a behavior-focused test before implementation code,
and describe any new local data written by the workbench.
