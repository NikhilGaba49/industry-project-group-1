# Industry Project Group 1

**Market Expansion and Revenue Optimisation** — a data-driven analysis of the Victorian rental market to guide where a property management agency should expand, which property features drive rent, and how to price rental properties.

## Project Overview

The objective is to **grow agency revenue**. The project answers three questions:

1. **What features drive rental price?** Linear-model feature importance, plus an XGBoost rental pricing model (test-set MAE of $58.20 / MAPE of 8.8%, versus $76.50 / 11.9% for a baseline linear regression).
2. **Which suburbs are predicted to grow the most?** ARIMA forecasts of suburb rent growth over five years (Sep 2026 to Sep 2031), built on 25 years of quarterly rent data ending 2025 Q3, and combined with recent lease counts as a proxy for market size.
3. **Which suburbs are most liveable and affordable?** A weighted liveability score (adapted from the Economist Intelligence Unit Global Liveability Index) and a rent-to-income affordability score, both expressed as percentiles across suburbs.

**Headline recommendation:** expand into Greater Bendigo (North Bendigo and Golden Square-Kangaroo Flat), pitch solar upgrades to landlords, and price every appraisal with the pricing model. The team also built a Rental Properties Dashboard with suburb median rent forecasts to 2031 and a property rent estimator with prediction intervals.

### Data sources

| Source | Data | Used for |
|---|---|---|
| Australian Bureau of Statistics | Population, income | Affordability |
| Victorian Government open data | Schools, parks and conservation reserves, crime by LGA, moving annual rent | Liveability and forecasts |
| Public Transport Victoria (PTV) | Train station and bus stop locations | Liveability and proximity features |
| OpenStreetMap (via the Overpass API) | Shopping centres, local parks, beaches, doctors, clinics and hospitals | Liveability and proximity features |
| HeiGIT / OpenRouteService (ORS) API | Road distances and travel times from each rental property to its nearest facilities | Proximity features |
| Rental listings (`rea_data`) | 12,000+ listings across Victoria: weekly rent and property features | Pricing model and rent drivers |

Distances to facilities are calculated using the OpenRouteService (ORS) API. Data is retrieved via external APIs, and API keys are stored locally (never committed).

### Known limitations

- Listings are asking rents, not agreed rents.
- Income data is from 2023, is per person (not per household) and is by SA2 area rather than suburb.
- Solar is under-reported in the rental data, and the solar rent premium is an association, not proven causation.
- 270 suburbs have fewer than 5 unique properties and so have no liveability score.

### Team

Nikhil Gaba, Jovi Nguyen, Mark Mchaileh, Agamjot Sandhu, Andy Nguyen.

## Pipeline

The Python notebooks in `notebooks/` clean and curate the rental listings, clean the external datasets (income, crime, population, historical rent), build facility-proximity features, merge everything together and fit the gradient boosted tree (GBT) pricing model. They also calculate the affordability and liveability scores. The R / Quarto files in `R_Markdown_Files/` handle the suburb rent forecasting and the explanatory (linear) model.

## Prerequisites

- Python 3.12 with Jupyter (or VS Code / JupyterLab) to run the notebooks
- Python packages, listed in `requirements.txt`. Install them from the repository root with:

  ```
  pip install -r requirements.txt
  ```
- A free [HeiGIT](https://account.heigit.org/signup) account and API key, for the OpenRouteService (ORS) API
- The provided `rea_data.zip`
- R 4.5.1 and Quarto (see [R Dependencies](#r-dependencies))

## Reproducing the Results

Follow these steps in order.

### 1. Download and extract the data

Download the provided `rea_data.zip` and extract it into a regular folder (i.e. outside the repository for now). This produces a folder named `rea_data`.

### 2. Copy the data into the repository

Copy the extracted `rea_data` folder into the root of the repository:

```
industry-project-group-1/
└── rea_data/
```

### 3. Create the landing folder

Inside `rea_data`, create a folder named `landing`, then copy the `domain` subfolder into it:

```
industry-project-group-1/
└── rea_data/
    └── landing/
        └── domain/
```

### 4. Add your ORS API key

1. Create a free HeiGIT account at [account.heigit.org/signup](https://account.heigit.org/signup). The account comes with a free Standard API key. (The notebooks call the HeiGIT-hosted OpenRouteService API at `api.heigit.org`, so the key must come from HeiGIT.)
2. Copy your API key from your [HeiGIT dashboard](https://account.heigit.org).
3. In the main `industry-project-group-1` folder, create a file named `.env` containing:

```
ORS_API_KEY="{insert key here}"
```

Replace `{insert key here}` with your own key. Do not commit this file. Make sure `.env` is listed in `.gitignore`.

### 5. Download the parks data (PARKRES)

The parks and conservation reserves data must be downloaded by placing a free order on DataShare Victoria:

1. Go to the [PARKRES dataset page](https://datashare.maps.vic.gov.au/search?md=51d86fdf-8a29-5e09-904f-855319faf2d8).
2. Select **Parkres** and click **Add to order**.
3. Use these order settings:
   - **Format:** ESRI Shapefile
   - **Projection:** Geographicals on GDA2020
   - **Buffer:** No buffer
   - **Area:** select all available area
4. Place the order (it is free). A download link for the zip file will be sent to your email.
5. Download and extract the zip file, rename the extracted folder to `parks`, and place it inside the `external_data` folder:

```
industry-project-group-1/
└── external_data/
    └── parks/
```

The rest of the files in `external_data/` are already provided in the repository.

### 6. Run the Python notebooks

Run **every cell** of each notebook, in the exact order below. Complete one folder before starting the next. All of these folders are inside `notebooks/`.

**6a. `Clean_Estate_data/`** (in this order)

1. `Raw_layer.ipynb`
2. `Curated_layer_1.ipynb`
3. `Curated_layer_2.ipynb`
4. `Curated_layer_3.ipynb`

**6b. `clean_non_features_external_data/`** (any order)

- `clean_abs_income.ipynb`
- `Clean_crime_rates.ipynb`
- `cleaning_population_datasets.ipynb`
- `refactoring_historical_rent_data.ipynb`

**6c. `External_Features_Processing/`** (in this order)

1. `clean_ptv_stops.ipynb`
2. `cleaning_sports_rec_facilities_data.ipynb`
3. `loading_parks_data.ipynb`
4. `school_features.ipynb`
5. `overpass_querying.ipynb` (queries OpenStreetMap, no API key needed)
6. `proximities_facilities.ipynb` (uses the ORS API: **see [ORS API Quota](#ors-api-quota) first, as this takes several days**)

**6d. `Merging_data/`** (in this order)

1. `Merging_crime_1.ipynb`
2. `Merging_Population_2.ipynb`
3. `Merging_income_3.ipynb`

**6e. `Modelling/`** (in this order)

1. `feature_engineering.ipynb`
2. `GBT Modelling.ipynb`

**6f. Notebooks directly in `notebooks/`** (not in a subfolder)

Run all of them (any order), including:

- `calculate_affordability.ipynb`
- `calculate_liveability.ipynb`
- `Rental_Listings_Visual.ipynb`

### 7. Render the R files

Run these **after** all the Python notebooks above. Set up the R environment first (see [R Dependencies](#r-dependencies)).

**Copy the forecasting input first.** `Modelling_rent.qmd` reads `rent_by_qtr_suburb_refactored.csv`, which is the output of `refactoring_historical_rent_data.ipynb` (step 6b). Copy that file into the `R_Markdown_Files/Suburb Rent Price Modelling/` folder, next to the `.qmd`.

Then render the following files from `R_Markdown_Files/`:

- `Suburb Rent Price Modelling/Modelling_rent.qmd` (render with Quarto). Rendering produces `Modelling_rent.html` and `Modelling Rent.pdf` in the same folder; these are only created if the file is rendered, not if the code chunks are just run. It also produces `top10_growth_by_year.csv`.
- `Weekly_Rent_Explanatory_Model_v5.Rmd` (knit in RStudio or with `rmarkdown::render()`)

`v5` is the only version of the explanatory model kept in the repository.

## ORS API Quota

`proximities_facilities.ipynb` (step 6c) makes a large number of ORS matrix requests, and the free ORS plan has daily and per-minute limits. **A full run takes several days.**

- The first pass alone needs about 1,670 requests across the 13 destination types. The second pass, third pass and full-search steps add more.
- The notebook caps each run at 450 requests (`MAX_REQUESTS_PER_RUN`) and waits 1.6 seconds between requests (`SECONDS_BETWEEN_REQUESTS`) to stay within the free-tier limits. Check the limits shown on your [HeiGIT dashboard](https://account.heigit.org) (the [HeiGIT API FAQ](https://giscience.github.io/openrouteservice/frequently-asked-questions#when-and-how-does-my-quota-reset) explains when quotas reset) and adjust these two values if yours differ.
- **It is OK if a code cell stops partway.** When the daily quota is reached (HTTP 429), the run cap is hit, or the cell is interrupted or errors, the notebook stops and (for quota and run cap) prints a message. This is expected, not a failure.
- **Resuming:** each batch is cached in `proximity_results/cache_*` as soon as it returns, so nothing already completed is lost. Simply rerun the same cell and it continues where it stopped. If there is still room left in that day's ORS quota, restart it straight away. Once the quota is used up, wait for it to reset (usually the next day) and then rerun.
- **Do not delete `proximity_results/` between runs**, or the cached requests are lost and will use up quota again.
- Run the cells top to bottom. Rerunning an earlier "run every destination" cell after a later pass overwrites the saved results with the earlier pass's output. The caches make redoing the later passes free of quota, but it costs time.
- Plan ahead: start this step early, and keep your ORS key private (the notebook reads it from `.env` or prompts for it).

## R Dependencies

R package versions are managed with [renv](https://rstudio.github.io/renv/) and recorded in `renv.lock`.

### Prerequisites

- R 4.5.1 (the version the lockfile was created with)
- [Quarto](https://quarto.org/docs/get-started/) to render the `.qmd` files
- On Windows, [Rtools](https://cran.r-project.org/bin/windows/Rtools/) may be needed if any package has to be compiled from source

### Setup

1. Open R (or RStudio) in the repository root, where `renv.lock` is located. renv will bootstrap itself automatically through `.Rprofile`.
2. Install the exact package versions:

   ```r
   renv::restore()
   ```

   Type `y` if prompted to proceed. The first run may take several minutes.

3. Check that everything is in sync:

   ```r
   renv::status()
   ```

## Final Folder Structure

```
industry-project-group-1/
├── digital_boundary_files/
├── external_data/                  # provided data files, plus parks/ (step 5)
│   ├── parks/
│   └── ...
├── Figures/
├── notebooks/
│   ├── Clean_Estate_data/
│   ├── clean_non_features_external_data/
│   ├── External_Features_Processing/
│   ├── Merging_data/
│   ├── Modelling/
│   ├── calculate_affordability.ipynb
│   ├── calculate_liveability.ipynb
│   └── Rental_Listings_Visual.ipynb
├── R_Markdown_Files/
│   ├── Suburb Rent Price Modelling/
│   │   ├── Modelling_rent.qmd
│   │   └── rent_by_qtr_suburb_refactored.csv
│   └── Weekly_Rent_Explanatory_Model_v5.Rmd
├── rea_data/                       # provided data, plus landing/domain/ (steps 2-3)
│   ├── landing/
│   │   └── domain/
│   └── ...                         # further folders are created by the notebooks
├── renv/
├── .env                            # your ORS key (step 4)
├── .gitignore
├── .Rprofile
├── renv.lock
├── requirements.txt
├── summary_notebook.ipynb
└── README.md
```

Only the main files and folders are shown. Other files created while running the notebooks (such as `proximity_results/`) are not listed.

## Troubleshooting

- **ORS errors (401/403):** check that `.env` is in the main project folder and the key is wrapped in quotes.
- **File not found errors:** confirm `rea_data/landing/domain/` exists exactly as shown above.
- **`Modelling_rent.qmd` can't find `rent_by_qtr_suburb_refactored.csv`:** copy it from the output of `refactoring_historical_rent_data.ipynb` into `R_Markdown_Files/Suburb Rent Price Modelling/` (see step 7).
- **Parks data not found:** confirm the extracted folder is named exactly `parks` and sits inside `external_data/`.
- **A notebook fails because an input file is missing:** an earlier notebook was probably skipped or run out of order. Rerun the earlier notebooks in the order given in step 6.
- **Notebooks fail partway:** run them in order and restart the kernel before re-running.
- **`renv::restore()` fails to install a package:** confirm you are on R 4.5.1 and, on Windows, that Rtools is installed.