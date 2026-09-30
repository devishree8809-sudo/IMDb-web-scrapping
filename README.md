# IMDb Top 250 Scraper

A Python Flask application that scrapes the IMDb Top 250 movies, saves the information to CSV, and presents the results in a polished dashboard with stats, searchable movie tables, and analytics charts.

## Features

- Scrape the IMDb Top 250 movie list using Selenium
- Save ranked data to CSV
- Display a dashboard with movie statistics
- Show a searchable and filterable list of all movies
- Present analytics charts with Chart.js
- Download the scraped dataset
- Switch between dark and light themes

## Technologies

- Python
- Flask
- Selenium
- webdriver-manager
- Pandas
- HTML5
- CSS3
- JavaScript
- Chart.js
- CSV

## Project Structure

```text
IMDb web scrapping/
├── app.py
├── scraper.py
├── requirements.txt
├── README.md
├── data/
│   └── imdb_top_250.csv
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── movies.html
│   ├── analytics.html
│   └── about.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── script.js
```

## Installation

1. Open a terminal in the project folder.
2. Create a virtual environment if desired:

```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the Scraper

```bash
python scraper.py
```

This will open Chrome, scrape the IMDb Top 250 page, and save the data to `data/imdb_top_250.csv`.

## Run the Flask App

```bash
python app.py
```

Then open the app in your browser at:

```text
http://127.0.0.1:5000
```

## Notes

- The scraper uses ChromeDriver managed automatically via webdriver-manager.
- If the CSV file is missing, the app will display a graceful empty state instead of crashing.
- The app can refresh data by visiting the /refresh route or using the Refresh Data button in the navbar.
