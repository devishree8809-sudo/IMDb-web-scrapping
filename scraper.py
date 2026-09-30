from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


DATA_DIR = Path(__file__).resolve().parent / 'data'
CSV_PATH = DATA_DIR / 'imdb_top_250.csv'
DEBUG_PATH = DATA_DIR / 'imdb_debug.html'
IMDB_TOP_250_URL = 'https://www.imdb.com/chart/top/'
EXPECTED_MOVIES = 250

# Current chart entries are list items containing a title heading and a /title/ link.
# This deliberately avoids depending on IMDb's generated CSS class names.
MOVIE_ITEM_XPATH = (
    '//li[.//*[@data-testid="title-list-item-ranking"]]'
    '[.//a[contains(@href, "/title/") and .//h4]]'
)
TITLE_SELECTOR = 'h4.ipc-title__text'
YEAR_SELECTOR = 'div.cli-title-metadata li.ipc-inline-list__item'
RATING_SELECTOR = '[data-testid="ratingGroup--imdb-rating"]'


def ensure_data_directory() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def setup_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--lang=en-US')
    options.add_argument('--log-level=3')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def save_debug_page(driver: webdriver.Chrome) -> None:
    ensure_data_directory()
    DEBUG_PATH.write_text(driver.page_source, encoding='utf-8')
    body = driver.find_element(By.TAG_NAME, 'body').text
    body_lower = body.lower()
    if 'verify you are human' in body_lower or 'robot check' in body_lower:
        print('Page classification: bot verification.')
    elif 'cookie' in body_lower and 'consent' in body_lower:
        print('Page classification: consent/cookie page.')
    elif 'sign in' in body_lower and 'IMDb Top 250 movies' not in body:
        print('Page classification: login page.')
    elif 'IMDb Top 250 movies' in body and '250 Titles' in body:
        print('Page classification: IMDb Top 250 chart.')
    else:
        print('Page classification: unknown IMDb response.')
    print(f'Debug URL: {driver.current_url}')
    print(f'Debug page title: {driver.title}')
    print(f'Debug document.readyState: {driver.execute_script("return document.readyState")}')
    print(f'Debug body text: {" ".join(body.split())[:800]}')
    print(f'Debug page source saved to: {DEBUG_PATH}')


def find_movie_items(driver: webdriver.Chrome) -> list:
    return driver.find_elements(By.XPATH, MOVIE_ITEM_XPATH)


def extract_movies(driver: webdriver.Chrome) -> list[dict]:
    print('Waiting for movie data...')
    wait = WebDriverWait(driver, 30)
    wait.until(lambda browser: find_movie_items(browser))

    previous_count = 0
    stable_passes = 0
    for _ in range(40):
        items = find_movie_items(driver)
        if len(items) >= EXPECTED_MOVIES:
            break
        current_count = len(items)
        driver.execute_script('window.scrollBy(0, Math.max(window.innerHeight * 0.8, 600));')
        try:
            WebDriverWait(driver, 4).until(
                lambda browser: len(find_movie_items(browser)) > current_count
                or browser.execute_script(
                    'return window.scrollY + window.innerHeight >= document.body.scrollHeight'
                )
            )
        except TimeoutException:
            pass
        new_count = len(find_movie_items(driver))
        stable_passes = stable_passes + 1 if new_count == previous_count else 0
        previous_count = new_count
        if stable_passes >= 3:
            break

    rows = find_movie_items(driver)
    print(f'Found {len(rows)} movie elements...')
    movies = []
    for movie_number, row in enumerate(rows[:EXPECTED_MOVIES], start=1):
        print(f'Scraping movie {movie_number}/250...')
        rank = movie_number
        title = None
        year = None
        rating = None
        try:
            rank_text = row.find_element(
                By.CSS_SELECTOR, '[data-testid="title-list-item-ranking"]'
            ).text.strip()
            match = re.search(r'\d+', rank_text)
            if match:
                rank = int(match.group())
            title = row.find_element(By.CSS_SELECTOR, TITLE_SELECTOR).text.strip()
        except (NoSuchElementException, WebDriverException) as error:
            print(f'Movie {movie_number}: title unavailable ({error}).')
        try:
            for item in row.find_elements(By.CSS_SELECTOR, YEAR_SELECTOR):
                match = re.fullmatch(r'\(?((?:18|19|20)\d{2})\)?', item.text.strip())
                if match:
                    year = int(match.group(1))
                    break
        except WebDriverException as error:
            print(f'Movie {movie_number}: year unavailable ({error}).')
        try:
            rating_elements = row.find_elements(By.CSS_SELECTOR, RATING_SELECTOR)
            if rating_elements:
                rating_text = rating_elements[0].get_attribute('aria-label') or rating_elements[0].text
                match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                if match:
                    rating = float(match.group(1))
        except WebDriverException as error:
            print(f'Movie {movie_number}: rating unavailable ({error}).')
        movies.append({'Rank': rank, 'Title': title or 'N/A', 'Year': year, 'IMDb Rating': rating})

    unique_movies = {}
    for movie in movies:
        if 1 <= movie['Rank'] <= EXPECTED_MOVIES and movie['Rank'] not in unique_movies:
            unique_movies[movie['Rank']] = movie
    return [unique_movies[rank] for rank in sorted(unique_movies)]


def save_movies_to_csv(movies: list[dict]) -> None:
    ensure_data_directory()
    columns = ['Rank', 'Title', 'Year', 'IMDb Rating']
    pd.DataFrame(movies, columns=columns).to_csv(CSV_PATH, index=False)


def print_top_10(movies: list[dict]) -> None:
    dataframe = pd.DataFrame(movies)
    dataframe['IMDb Rating'] = pd.to_numeric(dataframe['IMDb Rating'], errors='coerce')
    top_10 = dataframe.dropna(subset=['IMDb Rating']).sort_values('IMDb Rating', ascending=False).head(10)
    print('Top 10 Highest Rated Movies:')
    print('Rank | Title | Year | IMDb Rating')
    for _, movie in top_10.iterrows():
        year = int(movie['Year']) if pd.notna(movie['Year']) else 'N/A'
        print(f"{int(movie['Rank'])} | {movie['Title']} | {year} | {float(movie['IMDb Rating']):.1f}")


def scrape_imdb_top_250() -> list[dict]:
    print('Starting IMDb Top 250 Scraper...')
    driver = None
    try:
        driver = setup_driver()
        print('Opening IMDb Top 250 page...')
        driver.get(IMDB_TOP_250_URL)
        WebDriverWait(driver, 30).until(
            lambda browser: browser.execute_script('return document.readyState') == 'complete'
        )
        print('IMDb page loaded.')
        save_debug_page(driver)
        print('Finding movie elements...')
        movies = extract_movies(driver)
        print('Validating scraped data...')
        ranks = [movie['Rank'] for movie in movies]
        complete = len(movies) == EXPECTED_MOVIES and set(ranks) == set(range(1, EXPECTED_MOVIES + 1))
        print(f'Expected: {EXPECTED_MOVIES} movies')
        print(f'Actual: {len(movies)} movies')
        if not complete:
            print('Scrape incomplete. No CSV was saved.')
            return movies
        print('Successfully scraped: 250/250')
        print_top_10(movies)
        save_movies_to_csv(movies)
        print('CSV saved successfully.')
        return movies
    except TimeoutException as error:
        print(f'Timed out while loading IMDb movie data: {error}')
        if driver is not None:
            save_debug_page(driver)
        return []
    except WebDriverException as error:
        print(f'WebDriver error: {error}')
        return []
    except Exception as error:
        print(f'Unexpected scraper error: {error}')
        return []
    finally:
        if driver is not None:
            driver.quit()
            print('Browser closed successfully.')


if __name__ == '__main__':
    scrape_imdb_top_250()
