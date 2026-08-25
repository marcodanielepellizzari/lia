# Mining Isotope Database — Django app

Django application implementing the "Database Pb" spec slides: collecting
and organizing mineral deposit data, with a focus on **Pb isotope
ratios** (the core of the application -- the future analysis/
visualization pages will be built on this data), while trace elements
remain supporting metadata. Login/permissions with 4 roles, a 4-step
loading workflow (upload → mapping → validation → import) followed by
review/merge, and full web pages to manage all of it.

The data schema was designed by reading the columns of the real Excel
file (`Database ores dicembre 2023.xls`, 17 country sheets × ~113
columns each) provided as a sample of the data to be loaded.

## Project structure

```
mining_db/
  config/         # settings, urls, wsgi
  accounts/       # custom User + roles (Admin, Reviewer, Registered) + permission mixins
  catalog/        # ANAGRAPHICAL tables: Country, Locality, GeologicUnit,
                   # DepositType, Laboratory, AnalyticalMethod, Reference,
                   # ChemicalElement -- the "Deposit table" single source of truth
  datasets/       # FACT tables: Sample (+ trace_elements JSON), LeadIsotopeMeasurement,
                   # CopperIsotopeMeasurement
                   # + services.py: column mapping + import, shared by CLI and web
                   # + page_views.py: dataset pages + CSV upload wizard
                   # + management command import_samples (CLI loading)
                   # + DRF API (SampleViewSet, for future use: Pb analysis page)
  workflow/       # Dataset (with default_symbol/default_color for charts),
                   # DatasetShare, MergeRequest, SavedFilter, DataUsageLog
                   # + page_views.py: review queue, merge request approve/reject
  artifacts/      # ArtifactSet, Artifact: the user's own Pb isotope measurements
                   # on archaeological/artifact samples, uploaded (manually or via
                   # CSV) as an overlay data source for the analysis charts
  analysis/       # pb_diagrams page: lets the user pick which Datasets/ArtifactSets
                   # to plot, apply location/deposit-type/access filters, and
                   # renders the 3 standard Pb-Pb provenance diagrams (Plotly.js)
  templates/      # Bootstrap 5 via CDN, no frontend build step
```

## Available pages

| URL | Who can access it | What it does |
|---|---|---|
| `/datasets/` | everyone (Unregistered sees only public data) | dataset list |
| `/datasets/new/` | Registered+ | step 1: name, visibility, **default symbol and color** |
| `/datasets/<id>/` | based on visibility/ownership | dataset detail, samples, status |
| `/datasets/<id>/upload/` | owner | step 2: CSV/Excel upload |
| `/datasets/<id>/upload/map/` | owner | step 3: column mapping → DB fields (with guessed default) |
| `/datasets/<id>/upload/preview/` | owner | step 4: preview + confirm import |
| `/datasets/<id>/share/` | owner | sharing with other users |
| `/datasets/<id>/submit-review/` | owner | sends the merge request to the Reviewer |
| `/review/` | Reviewer, Admin | merge request queue |
| `/review/<id>/` | Reviewer, Admin | detail, notes, approve/reject |
| `/artifacts/` | Registered+ | list of the user's own artifact sets |
| `/artifacts/new/` | Registered+ | create an artifact set (name, default symbol/color) |
| `/artifacts/<id>/` | owner | artifact set detail, list of artifacts |
| `/artifacts/<id>/add/` | owner | add one artifact at a time (manual entry) |
| `/artifacts/<id>/upload-csv/` | owner | bulk upload artifacts from CSV |
| `/analysis/` | everyone (Unregistered sees only the public dataset) | the 3 Pb-Pb provenance diagrams (points or kernel density) plus a 3D scatter, with data-source and filter selection |
| `/accounts/login/`, `/accounts/logout/` | everyone | authentication |
| `/admin/` | Admin (Reviewer for anagraphical tables) | full Django Admin |
| `/api/samples/`, `/api/datasets/`, `/api/saved-filters/` | -- | DRF API for future use (analysis pages) |

## Why this schema

- **Pb isotopes at the center, trace elements as metadata**:
  `LeadIsotopeMeasurement` is indexed on the three standard denominators
  (206/204, 207/204, 208/204) used in Pb-Pb provenance diagrams. The
  other ~70 elements no longer have a dedicated relational table: they
  are a `JSONField` (`Sample.trace_elements`) -- simpler to maintain for
  data that gets looked up rather than queried in complex ways.
- **Symbol and color per dataset**: `Dataset.default_symbol` /
  `default_color`, chosen at upload step 1, will be the default with
  which samples from that dataset are drawn on future analysis pages
  (per-sample overrides will be possible later).
- **Deposit table single source of truth (slide 3)**: `Locality` is
  centralized; a sample can't have deposit coordinates/names disconnected
  from the ones already known, unlike what currently happens in the
  Excel sheet.
- **4+1 step workflow (slides 5-7)**: upload → mapping → preview →
  import (all in `datasets/page_views.py`, shared logic in
  `datasets/services.py`) → submit review → `MergeRequest` with
  approve/reject on the `/review/<id>/` page, which mirrors "Verify
  anagraphical fields → Add notes → Approve → Set permissions".
- **4 roles (slide 8/10)**: `accounts.Role` (Admin, Reviewer, Registered)
  + anonymous user for "Unregistered". Enforced in web pages
  (`accounts/mixins.py`: `RegisteredRequiredMixin`, `ReviewerRequiredMixin`,
  `AdminRequiredMixin`), in Django Admin, and in the DRF API.
- **Artifacts as an overlay, not part of the deposit database**: an
  `Artifact` (in the `artifacts` app) is deliberately a separate,
  lighter model from `datasets.Sample` -- no locality FK, no dataset
  review workflow. It's the user's own reference data (e.g. Pb isotope
  measurements on an archaeological find), meant to be compared against
  the deposit database on the analysis charts, not merged into it.
  `ArtifactSet` mirrors `Dataset`'s `default_symbol`/`default_color`
  idea, so both kinds of data source are visually consistent on the
  charts.
- **Three fixed diagrams, not a generic chart builder**: `analysis/
  page_views.py` always computes the three standard Pb-Pb binary ratios
  (206/204 vs 207/204, 206/204 vs 208/204, 207/206 vs 208/206) used in
  provenance studies, rather than letting the user pick arbitrary axes --
  matches how this data is actually read in the literature.
- **Kernel density as a server-side overlay, not a client-side histogram**:
  the "density" display mode computes a true Gaussian KDE (`scipy.stats.
  gaussian_kde`) per dataset per diagram, evaluated on a grid and sent to
  Plotly as a `contour` trace -- rather than Plotly's built-in
  `histogram2dcontour`, which bins rather than truly estimating a
  density. Artifacts always stay as discrete points in this mode: the
  point of a provenance study is comparing a handful of artifact
  measurements against a deposit "field", not a density of the artifacts
  themselves. Datasets with fewer than 5 valid points fall back to
  points automatically (a KDE from 2-3 samples isn't meaningful).
- **3D axes = the three 204Pb-normalized ratios**: 206/204, 207/204,
  208/204 are the only three of the five ratios that form a genuinely
  independent 3D space (207/206 and 208/206 are themselves ratios of two
  of those three). The 3D scatter always plots raw points (no 3D KDE --
  out of scope for now), and maps our symbol set onto Plotly's smaller
  scatter3d-compatible symbol list client-side.

## Local setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python manage.py makemigrations accounts catalog datasets workflow
python manage.py migrate
python manage.py createsuperuser   # will be the first Admin (set role=admin via shell/admin)

python manage.py runserver
```

> Note: this environment has no network access to install packages or
> Django itself, so this code has not been run/tested with `manage.py`
> or a real server. It's written to be syntactically correct and
> consistent with the Django 5.x / DRF 3.15 API (verified with
> `ast.parse` on every file), but it's worth running `makemigrations`
> and reading the output carefully the first time, especially for
> models with `OneToOneField`/`unique_together`, and trying the upload
> wizard by hand with a small test CSV before using it on real data.

## Loading data

**From the web** (recommended): log in → "New dataset" → upload the
file → map the columns (a default is already proposed based on known
headers) → check the preview → confirm. Then, from the dataset detail
page, "Submit for review".

**From the command line** (for bulk imports):
```bash
python manage.py import_samples liguria_dec2023.csv \
    --owner mario.rossi \
    --dataset-name "Liguria - December 2023" \
    --submit-for-review
```
Only works if the automatic mapping can guess all required fields
(Sample/Label, Country); otherwise use the web wizard.

## Suggested next steps

1. **Per-object permissions with django-guardian** (already installed
   but not yet used): today sharing goes through `DatasetShare` at the
   whole-dataset level; to share a single `Sample`, guardian permissions
   could be assigned directly on the objects.
2. **Login form template**: Django's `AuthenticationForm` doesn't have
   Bootstrap classes on its widgets; if a consistent style is needed, it
   can be replaced with a custom form or `django-widget-tweaks`.
3. **Deployment**: switch from SQLite to Postgres (already prepared in
   `settings.py` via environment variables) before going to production.
4. **Isotope-ratio range filters on the analysis page**: today the
   filters cover location/deposit-type/access level; adding min/max
   filters on the ratios themselves (reusing `datasets.filters.SampleFilter`'s
   `pb206_204_min`/`_max` pattern) would help narrow down visual clusters.
5. **Sharing artifact sets**: currently `ArtifactSet` has no equivalent
   of `DatasetShare` -- each user only sees their own. Worth adding if
   artifact data needs to be shared within a team, same as datasets.
