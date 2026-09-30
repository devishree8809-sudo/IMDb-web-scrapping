from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import Flask, Response, redirect, render_template, send_file, url_for

from scraper import CSV_PATH, scrape_imdb_top_250

app = Flask(__name__)

DATA_PATH = CSV_PATH


def load_movies_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        return pd.DataFrame(columns=['rank', 'title', 'year', 'rating'])

    try:
        df = pd.read_csv(DATA_PATH)
        # Normalize column names to lowercase keys used by the app
        col_map = {}
        for c in df.columns:
            lc = c.strip().lower()
            if lc in ('rank',):
                col_map[c] = 'rank'
            if lc in ('title',):
                col_map[c] = 'title'
            if lc in ('year',):
                col_map[c] = 'year'
            if lc in ('imdb rating', 'imdb_rating', 'rating'):
                col_map[c] = 'rating'

        df = df.rename(columns=col_map)
        # Ensure required columns exist
        for required in ('rank', 'title', 'year', 'rating'):
            if required not in df.columns:
                df[required] = None

        return df
    except Exception:
        return pd.DataFrame(columns=['rank', 'title', 'year', 'rating'])


def get_top_10_movies(df: pd.DataFrame) -> list[dict]:
    """Return top 10 movies by IMDb rating from the provided DataFrame.
    
    Preserves original IMDb Rank values. Returns an empty list on error or
    if insufficient data exists. Returns a list of dicts with keys:
    - position: ranking in top 10 (1-10)
    - imdb_rank: original IMDb rank from the dataset
    - title: movie title
    - year: release year
    - rating: IMDb rating
    """
    if df is None or df.empty:
        return []

    try:
        df_local = df.copy()
        
        # Normalize column names (handle both uppercase and lowercase variants)
        rating_col = None
        for col in df_local.columns:
            if col.lower() == 'imdb rating':
                rating_col = col
                break
        
        if rating_col is None:
            if 'rating' in df_local.columns:
                rating_col = 'rating'
            else:
                return []
        
        # Convert ratings to numeric and drop invalid rows
        df_local[rating_col] = pd.to_numeric(df_local[rating_col], errors='coerce')
        df_local = df_local.dropna(subset=[rating_col])
        
        if df_local.empty:
            return []
        
        # Sort by rating descending
        df_sorted = df_local.sort_values(by=[rating_col], ascending=False)
        top_df = df_sorted.head(10)
        
        top_list = []
        for position, (_, row) in enumerate(top_df.iterrows(), start=1):
            # Get original IMDb rank (preserve from dataset)
            imdb_rank = None
            for rank_col in ['Rank', 'rank']:
                if rank_col in row.index and pd.notna(row[rank_col]):
                    try:
                        imdb_rank = int(row[rank_col])
                        break
                    except (ValueError, TypeError):
                        pass
            
            # Get title
            title = None
            for title_col in ['Title', 'title']:
                if title_col in row.index and pd.notna(row[title_col]):
                    title = str(row[title_col]).strip()
                    break
            
            # Get year
            year = None
            for year_col in ['Year', 'year']:
                if year_col in row.index and pd.notna(row[year_col]):
                    try:
                        year = int(row[year_col])
                        break
                    except (ValueError, TypeError):
                        pass
            
            # Get rating
            rating = None
            try:
                rating = round(float(row[rating_col]), 1)
            except (ValueError, TypeError):
                pass
            
            top_list.append({
                'position': position,
                'imdb_rank': imdb_rank or 'N/A',
                'title': title or 'N/A',
                'year': year or 'N/A',
                'rating': rating or 'N/A',
            })
        
        return top_list
    except Exception as e:
        print(f'Error in get_top_10_movies: {e}')
        return []


def format_rating(value):
    if pd.isna(value):
        return 'N/A'
    return float(value)


@app.route('/')
def dashboard():
    df = load_movies_data()
    has_data = not df.empty

    # Ensure top_10 is always defined to avoid UnboundLocalError
    top_10 = []

    if has_data:
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
        df['rank'] = pd.to_numeric(df['rank'], errors='coerce')
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        total_movies = int(len(df))

        valid_ratings = df['rating'].dropna()
        if valid_ratings.empty:
            highest_rating = 'N/A'
            average_rating = 'N/A'
            top_movie = 'N/A'
        else:
            highest_rating = round(float(valid_ratings.max()), 2)
            average_rating = round(float(valid_ratings.mean()), 2)
            try:
                top_movie_entry = df.loc[df['rating'].idxmax()]
                top_movie = f"{top_movie_entry['title']} ({top_movie_entry['rating']})"
            except Exception:
                top_movie = 'N/A'
        last_updated = datetime.fromtimestamp(DATA_PATH.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        top_movies = df.sort_values('rating', ascending=False).head(5).to_dict('records')
        top_movies = [{
            'rank': int(movie['rank']) if pd.notna(movie['rank']) else 0,
            'title': movie['title'],
            'year': int(movie['year']) if pd.notna(movie['year']) else 'N/A',
            'rating': float(movie['rating']) if pd.notna(movie['rating']) else 'N/A',
        } for movie in top_movies]

        # Compute Top 10 using the helper to ensure consistent handling
        top_10 = get_top_10_movies(df)
    else:
        total_movies = 0
        highest_rating = 'N/A'
        average_rating = 'N/A'
        top_movie = 'N/A'
        last_updated = 'No data available'
        top_movies = []

    return render_template(
        'index.html',
        total_movies=total_movies,
        highest_rating=highest_rating,
        average_rating=average_rating,
        top_movie=top_movie,
        last_updated=last_updated,
        top_movies=top_movies,
        top_10=top_10,
        has_data=has_data,
    )


@app.route('/movies')
def movies_page():
    df = load_movies_data()
    has_data = not df.empty

    movies = []
    years = []
    if has_data:
        df = df.copy()
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
        df['rank'] = pd.to_numeric(df['rank'], errors='coerce')
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        years = sorted(df['year'].dropna().astype(int).unique().tolist())
        movies = df.sort_values(['rank'], ascending=True).to_dict('records')
        movies = [{
            'rank': int(movie['rank']) if pd.notna(movie['rank']) else 0,
            'title': movie['title'],
            'year': int(movie['year']) if pd.notna(movie['year']) else 0,
            'rating': float(movie['rating']) if pd.notna(movie['rating']) else 0.0,
        } for movie in movies]

    return render_template('movies.html', movies=movies, years=years, has_data=has_data)


@app.route('/analytics')
def analytics_page():
    df = load_movies_data()
    has_data = not df.empty

    chart_data = {
        'topMovies': [],
        'ratingDistribution': [],
        'moviesByYear': [],
        'decadeDistribution': [],
    }
    
    # Analytics cards data
    total_movies = 0
    average_rating = 'N/A'
    highest_rated_title = 'N/A'
    lowest_rated_title = 'N/A'

    if has_data:
        df = df.copy()
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        
        total_movies = int(len(df))
        
        valid_ratings = df['rating'].dropna()
        if not valid_ratings.empty:
            average_rating = round(float(valid_ratings.mean()), 2)
            highest_idx = df['rating'].idxmax()
            highest_rated_title = f"{df.loc[highest_idx, 'title']}"
            lowest_idx = df['rating'].idxmin()
            lowest_rated_title = f"{df.loc[lowest_idx, 'title']}"

        top_movies = df.sort_values('rating', ascending=False).head(10)
        chart_data['topMovies'] = [
            {'title': row['title'], 'rating': float(row['rating'])}
            for _, row in top_movies.iterrows()
        ]

        rating_bins = pd.cut(df['rating'].dropna(), bins=[0, 5, 6, 7, 8, 9, 10], include_lowest=True, right=False)
        rating_counts = rating_bins.value_counts().sort_index()
        chart_data['ratingDistribution'] = [
            {'label': f'{int(b.left):.0f}-{int(b.right if b.right < 10 else 10):.0f}+', 'count': int(count)}
            for b, count in rating_counts.items()
        ]

        year_counts = df['year'].dropna().astype(int).value_counts().sort_index()
        chart_data['moviesByYear'] = [
            {'year': int(year), 'count': int(count)}
            for year, count in year_counts.items()
        ]

        # Calculate decade distribution
        def get_decade(year):
            return int(year // 10) * 10
        
        df['decade'] = df['year'].apply(get_decade)
        decade_counts = df['decade'].value_counts().sort_index()
        chart_data['decadeDistribution'] = [
            {'label': f"{int(decade)}s", 'count': int(count)}
            for decade, count in decade_counts.items()
            if not pd.isna(decade)
        ]

    return render_template(
        'analytics.html',
        chart_data=chart_data,
        has_data=has_data,
        total_movies=total_movies,
        average_rating=average_rating,
        highest_rated_title=highest_rated_title,
        lowest_rated_title=lowest_rated_title,
    )




@app.route('/refresh')
def refresh_data():
    try:
        scrape_imdb_top_250()
    except Exception:
        return redirect(url_for('dashboard'))
    return redirect(url_for('dashboard'))


@app.route('/top-rated')
def top_rated_page():
    df = load_movies_data()
    has_data = not df.empty

    # Always provide a top10 list (possibly empty)
    top10 = get_top_10_movies(df) if has_data else []

    return render_template('top_rated.html', top10=top10, has_data=has_data)


@app.route('/download')
def download_csv():
    if not DATA_PATH.exists():
        return redirect(url_for('movies_page'))

    return send_file(DATA_PATH, mimetype='text/csv', as_attachment=True, download_name='imdb_top_250.csv')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
