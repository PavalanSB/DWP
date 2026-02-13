## Digital Wellness Strategy Platform

A browser-based SaaS-style web application that helps individuals monitor, analyze, and improve their digital lifestyle using interactive analytics and a simple machine learning model.

### Tech Stack

- **Backend**: Python, Flask, Flask-Login, Flask-SQLAlchemy, SQLite
- **Frontend**: HTML, Bootstrap 5, Chart.js
- **ML**: Scikit-learn Decision Tree classifier

### Features

- **Authentication**: Secure registration and login with hashed passwords.
- **Dashboard**: Wellness score (0–100), streak counter, consistency %, mood summary, burnout warning banner, goal progress bars, category distribution, mood trend.
- **Activity Tracking**: Screen time by category (Social, Learning, Entertainment, Productivity, Gaming), sleep, work/study, mood (Happy/Neutral/Stressed/Tired/Motivated), stress level (1–5), energy level (1–5).
- **Goals**: Set daily screen limit, study target, and sleep target in Settings; track completion on dashboard.
- **Analytics**: Daily screen time, weekly usage, category distribution (pie), stress trend, weekly category comparison (stacked bar).
- **Insights**: ML-based wellness classification (Healthy/Moderate/Unhealthy/Burnout Risk) with recommendations.
- **Burnout detection**: Rule-based warning when high screen time, low sleep, and high stress.
- **Profile & Settings**: Profile with avatar, theme, notifications, burnout alerts toggle, mood tracking toggle, daily goals, change password, reset activity data.

### Project Structure

- `app.py` – Application factory, route registration, wellness snapshot helper.
- `config.py` – Environment-based configuration.
- `extensions.py` – Flask extensions (SQLAlchemy, LoginManager).
- `models.py` – `User`, `Activity`, `WellnessSnapshot`, `Goal` models.
- `ml.py` – Decision Tree (8 features: category times, sleep, stress, energy) and Burnout Risk output.
- `utils/wellness_metrics.py` – Streak, consistency score, wellness score (0–100), burnout check.
- `views/` – Blueprints:
  - `auth.py` – Login, register, logout.
  - `dashboard.py` – Main dashboard (protected).
  - `activity.py` – Activity tracking and listing.
  - `analytics.py` – Analytics page.
  - `insights.py` – Insights page.
  - `profile.py` – Profile + password change.
  - `settings.py` – Theme, notifications, data reset.
  - `api.py` – JSON endpoints used by charts and insights.
- `templates/` – Responsive HTML templates with Bootstrap.
- `static/` – CSS styles.

### Setup & Run

1. **Create a virtual environment (recommended)**  
   On Windows (PowerShell):
   ```bash
   cd DWP
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**
   ```bash
   set FLASK_ENV=development
   python app.py
   ```

4. Open your browser and navigate to:
   - `http://127.0.0.1:5000/`

From there you can register a user, log in, add activity entries, and explore the dashboard, analytics, and insights.

**After upgrading** (new Activity fields, Goals table, User preferences): if you see database errors, delete the existing database so tables are recreated with the new schema. For a default SQLite setup, remove `instance/dwp.db` or `dwp.db` in the project root, then run the app again.

