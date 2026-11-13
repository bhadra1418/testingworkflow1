# DSA Application CSS Check — GitHub Actions

A minimal Python + Playwright + pytest project that checks whether
`https://dev-dsaapp.basichomeloan.com` responds and whether its stylesheets
are available in Chromium headless mode.

## Project structure

```text
dsa_playwright_github_actions/
├── .github/
│   └── workflows/
│       └── dsa-css-check.yml
├── tests/
│   └── test_dsa_app.py
├── conftest.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Add it to GitHub

1. Extract this ZIP.
2. Copy the files and folders into the root of your GitHub repository.
3. Ensure the workflow is at exactly:
   `.github/workflows/dsa-css-check.yml`
4. Commit and push the changes.
5. Open the repository on GitHub → **Actions** → **DSA Application CSS Check**.
6. Select **Run workflow**, or push to `main` / open a pull request targeting `main`.

## View screenshots and logs

After the workflow finishes:

1. Open the workflow run.
2. Scroll to **Artifacts**.
3. Download `dsa-css-check-artifacts`.
4. Open `dsa-homepage.png`.

The test also prints failed requests and HTTP errors in the workflow log.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
pytest -v -s tests/test_dsa_app.py
```

## Notes

- The GitHub-hosted runner must be able to reach the DSA URL. If the application
  is restricted to a VPN, office network, or IP allowlist, the hosted runner
  may not be able to access it; use an appropriately configured self-hosted
  runner or allow the runner network.
- This checks stylesheet loading, not pixel-perfect visual correctness.
- A stylesheet link with `link.sheet` available does not prove every CSS rule
  has applied. For deeper diagnosis, inspect browser console errors and
  computed styles.
- If the application needs authentication before the page renders, add the
  approved test login flow before the CSS assertions. Do not commit passwords
  or tokens; store them as GitHub Actions secrets.
