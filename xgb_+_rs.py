# -*- coding: utf-8 -*-
"""XGB + RS.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1Kkq1cbl4Fw--6ryo20S5MT0Kt0hJEo1U
"""

!pip install scikit-optimize
!pip install requests
!pip install optuna
!pip install catboost

"""# Import Library"""

# Import libraries
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import xgboost as xgb
import lightgbm as lgb
import catboost as cb
import optuna
import time
import shap
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, TimeSeriesSplit, RandomizedSearchCV, GridSearchCV
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.feature_selection import SelectFromModel
from scipy.stats import uniform, randint
from skopt import BayesSearchCV
from skopt.space import Real, Integer

# Suppress warnings
warnings.filterwarnings('ignore')

# Mount Google Drive and load dataset
from google.colab import drive
drive.mount('/content/drive')

file_path = '/content/drive/My Drive/Dataset/dataset_merged.xlsx'
df = pd.read_excel(file_path)
print(f"Dataset loaded with {df.shape[0]} rows and {df.shape[1]} columns.")

"""# Data Cleaning

"""

# Standarisasi nama kolom
original_columns = df.columns.tolist()
df.columns = df.columns.str.strip().str.replace(" ", "_", regex=False)

# Check missing values
missing_values = df.isnull().sum()
missing_values = missing_values[missing_values > 0]

plt.figure(figsize=(10, 8))
plt.barh(range(len(df.columns)), [1]*len(df.columns))  # Membuat semua batang dengan tinggi 1
plt.yticks(range(len(df.columns)), df.columns)
plt.title('Daftar Fitur dalam Dataset')
plt.xlabel('Jumlah')
plt.ylabel('Fitur (Kolom)')
plt.tight_layout()
plt.show()

# Data Cleaning
df['Size'] = df['Size'].fillna('All_Size').astype(str).str.replace("Ld ", "", case=False).str.strip()
df['Payment_platform_discount'] = pd.to_numeric(df['Payment_platform_discount'], errors='coerce').fillna(0)
df['Handling_Fee'] = pd.to_numeric(df['Handling_Fee'], errors='coerce').fillna(0)

"""# Feature Engineering

Time Extraction
"""

original_columns = df.columns.tolist()

# Feature Engineering - Time Features
if 'Created_Time' in df.columns:
    df['Created_Time'] = pd.to_datetime(df['Created_Time'], errors='coerce', dayfirst=True)
    df.dropna(subset=['Created_Time'], inplace=True)

# Extract basic time features
df['year'] = df['Created_Time'].dt.year
df['month'] = df['Created_Time'].dt.month
df['day'] = df['Created_Time'].dt.day
df['hour'] = df['Created_Time'].dt.hour
df['minute'] = df['Created_Time'].dt.minute
df['second'] = df['Created_Time'].dt.second
df['day_of_week'] = df['Created_Time'].dt.dayofweek
df['day_of_year'] = df['Created_Time'].dt.dayofyear
df['quarter'] = df['Created_Time'].dt.quarter
df['week_of_year'] = df['Created_Time'].dt.isocalendar().week

# Cyclical transformations
df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
df['day_of_week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
df['day_of_year_sin'] = np.sin(2 * np.pi * df['day_of_year'] / 365)
df['day_of_year_cos'] = np.cos(2 * np.pi * df['day_of_year'] / 365)
df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

# Calendar/event features
df['is_payday'] = df['day'].isin([25, 26, 27, 28, 29, 30, 31, 1, 2]).astype(int)
df['date'] = df['Created_Time'].dt.date
df['year_month'] = df['Created_Time'].dt.strftime('%Y-%m')
df['year_week'] = df['year'].astype(str) + '-' + df['week_of_year'].astype(str).str.zfill(2)

# Flash sale features
flash_dates = [f"{str(i).zfill(2)}-{str(i).zfill(2)}" for i in range(1, 13)]
df['flash_date_str'] = df['month'].astype(str).str.zfill(2) + '-' + df['day'].astype(str).str.zfill(2)
df['is_flash_sale'] = df['flash_date_str'].isin(flash_dates).astype(int)

# National holidays
years = [2022, 2023, 2024, 2025]
holiday_dates = []

for year in years:
    url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/ID"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        for holiday in data:
            holiday_dates.append(holiday['date'])

libur_nasional = pd.to_datetime(holiday_dates)
df['is_holiday'] = df['Created_Time'].dt.date.isin(libur_nasional.date).astype(int)

# Additional flags
df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
df['is_business_hour'] = (((df['hour'] >= 8) & (df['hour'] <= 17)) & (df['day_of_week'] < 5)).astype(int)
df['is_month_start'] = (df['day'] <= 7).astype(int)
df['is_month_end'] = (df['day'] >= 24).astype(int)

after_time_columns = df.columns.tolist()
added_time_features = [col for col in after_time_columns if col not in original_columns]

# Visualisasi
if added_time_features:
    fig, ax = plt.subplots(figsize=(8, len(added_time_features) * 0.3))
    bars = ax.barh(added_time_features, [1]*len(added_time_features), edgecolor='black')

    for bar in bars:
        ax.text(1.05, bar.get_y() + bar.get_height()/2, '1', va='center', fontsize=10)

    ax.set_title('Fitur Baru dari Feature Engineering Waktu', fontsize=14, pad=10)
    ax.set_xlabel('Fitur Baru')
    ax.set_xlim(0, 1.2)
    ax.set_xticks([])
    ax.invert_yaxis()
    plt.subplots_adjust(left=0.25, right=0.95, top=0.95, bottom=0.05)
    plt.grid(False)
    plt.show()

"""Time - Series"""

# Feature Engineering - Time Series Features
df = df.sort_values('Created_Time')
df['date'] = df['Created_Time'].dt.date

if 'Product_Name' in df.columns and 'Created_Time' in df.columns:
    # Daily sales aggregation per product
    daily_sales = df.groupby(['Product_Name', 'date'])['Quantity'].sum().reset_index()
    daily_sales = daily_sales.sort_values(['Product_Name', 'date'])

    # Create lag features
    for lag in [1, 7, 14, 30]:
        daily_sales[f'lag_{lag}_days'] = daily_sales.groupby('Product_Name')['Quantity'].shift(lag)

    # Moving Averages & Rolling Sum
    for window in [7, 14, 30]:
        daily_sales[f'moving_avg_{window}'] = daily_sales.groupby('Product_Name')['Quantity'].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean()
        )
        daily_sales[f'rolling_sum_{window}'] = daily_sales.groupby('Product_Name')['Quantity'].transform(
            lambda x: x.rolling(window=window, min_periods=1).sum()
        )

    # Merge time series features to main dataframe
    df = pd.merge(
        df,
        daily_sales[['Product_Name', 'date'] +
                    [f'lag_{lag}_days' for lag in [1, 7, 14, 30]] +
                    [f'moving_avg_{window}' for window in [7, 14, 30]] +
                    [f'rolling_sum_{window}' for window in [7, 14, 30]]],
        on=['Product_Name', 'date'],
        how='left'
    )

    # Volatility features
    df['demand_std_7days'] = daily_sales.groupby('Product_Name')['Quantity'].transform(
        lambda x: x.rolling(window=7, min_periods=1).std()
    )

    # Sales trends and ratios
    df['sales_trend'] = (df['lag_7_days'] - df['lag_14_days']) / (df['lag_14_days'] + 1) * 100
    df['sales_ratio_to_avg'] = df['Quantity'] / (df['moving_avg_30'] + 1)

# Flash sale features
df['flash_sale_yesterday'] = df.groupby('Product_Name')['is_flash_sale'].shift(1).fillna(0)
df['days_since_last_flash'] = (
    df[::-1].groupby('Product_Name')['is_flash_sale']
    .apply(lambda x: x.cumsum().shift(-1).fillna(0))
    .reset_index(level=0, drop=True)[::-1]
)

# Holiday and payday features
df['holiday_yesterday'] = df['is_holiday'].shift(1).fillna(0)
df['payday_yesterday'] = df['is_payday'].shift(1).fillna(0)

# Additional time features
df['week_of_month'] = pd.to_datetime(df['date']).dt.day.apply(lambda d: (d - 1) // 7 + 1)

# Monthly seasonal index
if 'month' in df.columns:
    # Calculate monthly average per product
    monthly_avg = df.groupby(['Product_Name', 'month'])['Quantity'].mean().reset_index()

    # Calculate overall average per product
    product_avg = monthly_avg.groupby('Product_Name')['Quantity'].mean().reset_index()

    # Join to calculate seasonal index
    monthly_avg = pd.merge(monthly_avg, product_avg, on='Product_Name', suffixes=('_month', '_product'))
    monthly_avg['seasonal_index'] = monthly_avg['Quantity_month'] / monthly_avg['Quantity_product']

    # Join seasonal index to main dataframe
    df = pd.merge(df, monthly_avg[['Product_Name', 'month', 'seasonal_index']],
                  on=['Product_Name', 'month'], how='left')

# Fill NaN values for all time series features
ts_columns = [col for col in df.columns if 'lag_' in col or 'moving_avg_' in col or
              'trend' in col or 'ratio' in col or 'seasonal' in col or
              'std' in col or 'flash' in col or 'holiday_yesterday' in col or
              'payday_yesterday' in col]
for col in ts_columns:
    if col in df.columns:
        df[col] = df[col].fillna(0)

# Drop and Save
created_times = df['Created_Time'].copy()
product_names = df['Product_Name'].copy()
variations = df['Variation'].copy() if 'Variation' in df.columns else None
sizes = df['Size'].copy() if 'Size' in df.columns else None

# Drop non-feature columns
df.drop(columns=['Created_Time', 'date', 'year_month', 'year_week'], inplace=True, errors='ignore')
df.drop(columns=['Product_Name', 'Variation', 'Size'], inplace=True, errors='ignore')

after_ts_columns = df.columns.tolist()
added_ts_features = [col for col in after_ts_columns if col not in after_time_columns]

# Visualisasi
if added_ts_features:
    fig, ax = plt.subplots(figsize=(8, len(added_ts_features) * 0.3))
    bars = ax.barh(added_ts_features, [1]*len(added_ts_features), edgecolor='black')

    for bar in bars:
        ax.text(1.05, bar.get_y() + bar.get_height()/2, '1', va='center', fontsize=10)

    ax.set_title('Fitur Baru dari Feature Engineering Time Series', fontsize=14, pad=10)
    ax.set_xlabel('Fitur Baru')
    ax.set_xlim(0, 1.2)
    ax.set_xticks([])
    ax.invert_yaxis()
    plt.subplots_adjust(left=0.25, right=0.95, top=0.95, bottom=0.05)
    plt.grid(False)
    plt.show()

"""# Data Split"""

# Train-Validation-Test Split
target_column = 'Quantity'
columns_to_drop = ['year_month', 'date', 'flash_date_str']

# Separate features and target
X = df.drop(columns=[target_column] + [col for col in columns_to_drop if col in df.columns])
y = np.log1p(df[target_column])  # Log transform for better model performance

# Time-based split
train_size = int(0.8 * len(df))
valid_size = int(0.1 * len(df))

X_train = X.iloc[:train_size]
y_train = y.iloc[:train_size]
X_valid = X.iloc[train_size:train_size+valid_size]
y_valid = y.iloc[train_size:train_size+valid_size]
X_test = X.iloc[train_size+valid_size:]
y_test = y.iloc[train_size+valid_size:]

# Hitung jumlah sampel
counts = [len(X_train), len(X_valid), len(X_test)]
labels = ['Training', 'Validation', 'Testing']
percentages = [count / (len(X_train) + len(X_valid) + len(X_test)) * 100 for count in counts]

# Visualisasi
print("Distribusi Jumlah Data:")
print(f"Training\t: {counts[0]} sampel ({percentages[0]:.1f}%)")
print(f"Validation\t: {counts[1]} sampel ({percentages[1]:.1f}%)")
print(f"Testing\t\t: {counts[2]} sampel ({percentages[2]:.1f}%)")
print(f"Total\t\t: {sum(counts)} sampel (100%)")

plt.figure(figsize=(8, 5))
sns.barplot(x=labels, y=counts, hue=labels, palette='Set2', legend=False)

for i, (count, pct) in enumerate(zip(counts, percentages)):
    plt.text(i, count + 5, f'{pct:.1f}%', ha='center', va='bottom', fontsize=12)

plt.title('Distribusi Data: Train / Validation / Test')
plt.ylabel('Jumlah Sampel')
plt.grid(True, axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()

# ==============================================
# KONFIGURASI PARAMETER
# ==============================================
top_k = 10  # Jumlah fitur yang akan dipilih
verbose = True  # Print progress atau tidak

print("🚀 Memulai Ensemble SHAP Feature Selection...")
print(f"📊 Dataset awal: {X_train.shape[1]} fitur, {X_train.shape[0]} sampel training")
print("=" * 60)

# ==============================================
# DEFINE MODELS
# ==============================================
models = {
    'XGBoost': xgb.XGBRegressor(
        random_state=42,
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        verbosity=0
    ),
    'LightGBM': lgb.LGBMRegressor(
        random_state=42,
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        verbosity=-1
    ),
    'CatBoost': cb.CatBoostRegressor(
        random_state=42,
        iterations=100,
        depth=6,
        learning_rate=0.1,
        verbose=False
    ),
    'RandomForest': RandomForestRegressor(
        random_state=42,
        n_estimators=100,
        max_depth=6
    )
}

# ==============================================
# CALCULATE SHAP VALUES FOR EACH MODEL
# ==============================================
all_shap_importance = []
individual_shap_scores = {}
model_performance = {}

# Loop untuk setiap model
for name, model in models.items():
    if verbose:
        print(f"🔄 Processing {name}...")

    try:
        # Train model pada data training
        model.fit(X_train, y_train)

        # Evaluasi performa model
        y_pred = model.predict(X_valid)
        rmse = np.sqrt(mean_squared_error(y_valid, y_pred))
        r2 = r2_score(y_valid, y_pred)
        model_performance[name] = {'RMSE': rmse, 'R2': r2}

        # Hitung SHAP values (gunakan sample 500 untuk efisiensi)
        explainer = shap.Explainer(model)
        shap_values = explainer(X_train.iloc[:500])
        importance = np.abs(shap_values.values).mean(axis=0)

        # Normalisasi importance ke skala 0-1
        importance_normalized = (importance - importance.min()) / (importance.max() - importance.min())

        all_shap_importance.append(importance_normalized)
        individual_shap_scores[name] = importance_normalized

        if verbose:
            print(f"   ✅ {name} - RMSE: {rmse:.4f}, R2: {r2:.4f}")

    except Exception as e:
        if verbose:
            print(f"   ❌ Error pada {name}: {str(e)}")
        continue

# Check jika ada model yang berhasil
if len(all_shap_importance) == 0:
    raise ValueError("Tidak ada model yang berhasil dihitung SHAP values-nya!")

# ==============================================
# ENSEMBLE SHAP IMPORTANCE
# ==============================================
print("\n🔄 Menghitung ensemble importance...")

# Rata-rata importance dari semua model (equal weight)
ensemble_importance = np.mean(all_shap_importance, axis=0)

# Buat DataFrame untuk analisis
feature_importance_df = pd.DataFrame({
    'Feature': X_train.columns,
    'Ensemble_Importance': ensemble_importance
})

# Tambahkan individual scores untuk analisis
for name, scores in individual_shap_scores.items():
    feature_importance_df[f'{name}_Importance'] = scores

# Sort berdasarkan ensemble importance
feature_importance_df = feature_importance_df.sort_values(
    by='Ensemble_Importance',
    ascending=False
).reset_index(drop=True)

# ==============================================
# SELECT TOP FEATURES
# ==============================================
selected_features = feature_importance_df['Feature'].iloc[:top_k].tolist()

# Apply feature selection ke dataset
X_train_selected = X_train[selected_features]
X_valid_selected = X_valid[selected_features]
X_test_selected = X_test[selected_features]

print(f"\n✅ Feature selection selesai!")
print(f"📊 Terpilih {len(selected_features)} fitur dari {X_train.shape[1]} fitur awal")
print(f"🎯 Top 5 fitur: {selected_features[:5]}")
print(f"📈 Rata-rata ensemble importance: {feature_importance_df['Ensemble_Importance'].mean():.4f}")

# ==============================================
# VISUALISASI HASIL
# ==============================================

# 1. Bar Chart - Ensemble Importance
print("\n📊 Visualisasi: Ensemble SHAP Importance")
plot_data = feature_importance_df.head(top_k).copy()

plt.figure(figsize=(12, 8))
bars = plt.barh(
    range(len(plot_data)),
    plot_data['Ensemble_Importance'],
    color=plt.cm.viridis(np.linspace(0, 1, len(plot_data)))
)

plt.yticks(range(len(plot_data)), plot_data['Feature'])
plt.xlabel('Ensemble SHAP Importance Score', fontsize=12, fontweight='bold')
plt.ylabel('Features', fontsize=12, fontweight='bold')
plt.title(f'Top {top_k} Features - Ensemble SHAP (XGB + LGBM + CatBoost + RF)',
          fontsize=14, fontweight='bold', pad=20)

# Tambahkan nilai pada bar
for i, (bar, val) in enumerate(zip(bars, plot_data['Ensemble_Importance'])):
    plt.text(val + 0.005, bar.get_y() + bar.get_height()/2,
            f'{val:.3f}', va='center', fontweight='bold')

plt.grid(True, axis='x', linestyle='--', alpha=0.3)
plt.tight_layout()
plt.show()

# 2. Heatmap - SHAP Score per Model
model_cols = [col for col in plot_data.columns if col.endswith('_Importance')]
if len(model_cols) > 0:
    print("\n📊 Visualisasi: SHAP Importance Per Model")
    fig, ax = plt.subplots(figsize=(14, 8))

    heatmap_data = plot_data[['Feature'] + model_cols].set_index('Feature')
    heatmap_data.columns = [col.replace('_Importance', '') for col in heatmap_data.columns]

    sns.heatmap(
        heatmap_data.T,
        annot=True,
        fmt='.3f',
        cmap='viridis',
        cbar_kws={'label': 'SHAP Importance Score'},
        linewidths=0.5
    )

    plt.title(f'Individual Model SHAP Importance - Top {top_k} Features',
              fontsize=14, fontweight='bold', pad=20)
    plt.xlabel('Features', fontsize=12, fontweight='bold')
    plt.ylabel('Models', fontsize=12, fontweight='bold')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

# ==============================================
# ANALISIS KONSENSUS ANTAR MODEL
# ==============================================
print("\n" + "="*60)
print("📊 ANALISIS KONSENSUS ANTAR MODEL")
print("="*60)

top_features = feature_importance_df.head(top_k)
model_scores = top_features[model_cols].values
consensus_scores = np.std(model_scores, axis=1)  # Standard deviation sebagai measure konsensus

# Buat analysis DataFrame
analysis_df = top_features[['Feature', 'Ensemble_Importance']].copy()
analysis_df['Consensus_Score'] = consensus_scores
analysis_df['Consensus_Level'] = pd.cut(
    consensus_scores,
    bins=3,
    labels=['High Consensus', 'Medium Consensus', 'Low Consensus']
)

print(f"🎯 Top {top_k} features dengan tingkat konsensus:")
print(analysis_df[['Feature', 'Ensemble_Importance', 'Consensus_Level']].to_string(index=False))

# Summary konsensus
consensus_summary = analysis_df['Consensus_Level'].value_counts()
print(f"\n📈 Ringkasan Konsensus:")
for level, count in consensus_summary.items():
    print(f"   {level}: {count} fitur")

# Baseline Model
print("=== BASELINE MODEL ===")
model_baseline = xgb.XGBRegressor(random_state=42, eval_metric=["rmse"])

# Create DMatrix for training and validation
dtrain = xgb.DMatrix(X_train, label=y_train)
dvalid = xgb.DMatrix(X_valid, label=y_valid)

# Set basic model parameters
params_baseline = {
    'objective': 'reg:squarederror',
    'eval_metric': 'rmse',
    'random_state': 42
}

# Prepare eval_set and evaluation results dictionary
evals = [(dtrain, 'train'), (dvalid, 'valid')]
evals_result_baseline = {}

# Train baseline with early stopping
model_baseline_xgb = xgb.train(
    params=params_baseline,
    dtrain=dtrain,
    num_boost_round=1000,
    evals=evals,
    early_stopping_rounds=20,
    evals_result=evals_result_baseline,
    verbose_eval=False
)

# Visualize baseline learning curve
rmse_train_baseline = np.array(evals_result_baseline['train']['rmse'])
rmse_valid_baseline = np.array(evals_result_baseline['valid']['rmse'])
mse_train_baseline = rmse_train_baseline ** 2
mse_valid_baseline = rmse_valid_baseline ** 2

plt.figure(figsize=(10, 6))
plt.plot(mse_train_baseline, label='Train MSE')
plt.plot(mse_valid_baseline, label='Validation MSE')
plt.axvline(x=model_baseline_xgb.best_iteration, color='r', linestyle='--', label='Best Iteration')
plt.title("XGBoost Baseline - MSE Learning Curve")
plt.xlabel("Boosting Rounds")
plt.ylabel("MSE")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# 3. RANDOM SEARCH
print("\n3. Starting Random Search...")

tscv = TimeSeriesSplit(n_splits=3)

param_random = {
    'max_depth': randint(3, 11),
    'learning_rate': uniform(loc=0.001, scale=0.999),  # 0.001–1.0
    'n_estimators': randint(50, 501),
    'subsample': uniform(loc=0.6, scale=0.4),  # 0.6–1.0
    'colsample_bytree': uniform(loc=0.6, scale=0.4),  # 0.6–1.0
}

model_xgb_random = xgb.XGBRegressor(
    objective='reg:squarederror',
    random_state=42,
    verbosity=0
)

random_search = RandomizedSearchCV(
    estimator=model_xgb_random,
    param_distributions=param_random,
    n_iter=100,
    cv=tscv,
    scoring='neg_mean_squared_error',
    n_jobs=1,
    verbose=3,
    random_state=42,
    return_train_score=True
)

start_random = time.time()
random_search.fit(X_train, y_train)
end_random = time.time()
print(f"Random Search completed in {(end_random - start_random) / 60:.2f} minutes.")

model_random = random_search.best_estimator_
best_params_random = random_search.best_params_
print("Best Random Search Parameters:", best_params_random)

# DETAILED LEARNING CURVES FOR RANDOM SEARCH
print("\n=== GENERATING LEARNING CURVES (Random Search Only) ===")

def plot_learning_curves(model_params, model_name, dtrain, dvalid, y_train, y_valid):
    """Generate comprehensive learning curves for a model"""

    # Prepare parameters
    params = model_params.copy()
    params.update({
        'objective': 'reg:squarederror',
        'eval_metric': 'rmse',
        'verbosity': 0,
        'random_state': 42
    })

    # Remove sklearn-specific parameters that xgb.train doesn't accept
    sklearn_params = ['n_estimators']
    for param in sklearn_params:
        if param in params:
            del params[param]

    # Prepare eval list and results dictionary
    evals = [(dtrain, 'train'), (dvalid, 'valid')]
    evals_result = {}

    # Train model with early stopping
    model = xgb.train(
        params=params,
        dtrain=dtrain,
        num_boost_round=1000,
        evals=evals,
        early_stopping_rounds=20,
        evals_result=evals_result,
        verbose_eval=False
    )

    # Get RMSE and convert to MSE
    rmse_train = np.array(evals_result['train']['rmse'])
    rmse_valid = np.array(evals_result['valid']['rmse'])
    mse_train = rmse_train ** 2
    mse_valid = rmse_valid ** 2

    # Create subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'{model_name} - Comprehensive Learning Curves', fontsize=16)

    # MSE
    axes[0, 0].plot(mse_train, label='Train MSE', alpha=0.8)
    axes[0, 0].plot(mse_valid, label='Validation MSE', alpha=0.8)
    axes[0, 0].axvline(x=model.best_iteration, color='r', linestyle='--', label='Best Iteration')
    axes[0, 0].set_title("MSE Learning Curve")
    axes[0, 0].set_xlabel("Boosting Rounds")
    axes[0, 0].set_ylabel("MSE")
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # RMSE
    axes[0, 1].plot(rmse_train, label='Train RMSE', alpha=0.8)
    axes[0, 1].plot(rmse_valid, label='Validation RMSE', alpha=0.8)
    axes[0, 1].axvline(x=model.best_iteration, color='r', linestyle='--', label='Best Iteration')
    axes[0, 1].set_title("RMSE Learning Curve")
    axes[0, 1].set_xlabel("Boosting Rounds")
    axes[0, 1].set_ylabel("RMSE")
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    # MAE
    mae_train = []
    mae_valid = []
    for i in range(1, min(model.best_iteration + 2, len(rmse_train) + 1)):
        y_pred_train_i = model.predict(dtrain, iteration_range=(0, i))
        y_pred_valid_i = model.predict(dvalid, iteration_range=(0, i))
        mae_train.append(mean_absolute_error(y_train, y_pred_train_i))
        mae_valid.append(mean_absolute_error(y_valid, y_pred_valid_i))

    axes[1, 0].plot(mae_train, label='Train MAE', alpha=0.8)
    axes[1, 0].plot(mae_valid, label='Validation MAE', alpha=0.8)
    axes[1, 0].axvline(x=model.best_iteration, color='r', linestyle='--', label='Best Iteration')
    axes[1, 0].set_title("MAE Learning Curve")
    axes[1, 0].set_xlabel("Boosting Rounds")
    axes[1, 0].set_ylabel("MAE")
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)

    # R²
    r2_train = []
    r2_valid = []
    for i in range(1, min(model.best_iteration + 2, len(rmse_train) + 1)):
        y_pred_train_i = model.predict(dtrain, iteration_range=(0, i))
        y_pred_valid_i = model.predict(dvalid, iteration_range=(0, i))
        r2_train.append(r2_score(y_train, y_pred_train_i))
        r2_valid.append(r2_score(y_valid, y_pred_valid_i))

    axes[1, 1].plot(r2_train, label='Train R²', alpha=0.8)
    axes[1, 1].plot(r2_valid, label='Validation R²', alpha=0.8)
    axes[1, 1].axvline(x=model.best_iteration, color='r', linestyle='--', label='Best Iteration')
    axes[1, 1].set_title("R² Learning Curve")
    axes[1, 1].set_xlabel("Boosting Rounds")
    axes[1, 1].set_ylabel("R² Score")
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    return model

# Hanya jalankan untuk Random Search
model_random_detailed = plot_learning_curves(best_params_random, "Random Search Optimization", dtrain, dvalid, y_train, y_valid)

print("\n=== MODEL EVALUATION AND COMPARISON (Random Search Only) ===")

# Fit baseline model
model_baseline.fit(X_train, y_train)

# Make predictions
y_pred_test_baseline = model_baseline.predict(X_test)
y_pred_test_random = model_random.predict(X_test)

# Calculate metrics
models_metrics = {
    'Baseline': {
        'MSE': mean_squared_error(y_test, y_pred_test_baseline),
        'RMSE': np.sqrt(mean_squared_error(y_test, y_pred_test_baseline)),
        'MAE': mean_absolute_error(y_test, y_pred_test_baseline),
        'R²': r2_score(y_test, y_pred_test_baseline)
    },
    'Random_Search': {
        'MSE': mean_squared_error(y_test, y_pred_test_random),
        'RMSE': np.sqrt(mean_squared_error(y_test, y_pred_test_random)),
        'MAE': mean_absolute_error(y_test, y_pred_test_random),
        'R²': r2_score(y_test, y_pred_test_random)
    }
}

# Comparison DataFrame
metrics_df = pd.DataFrame({
    'Metric': ['MSE', 'RMSE', 'MAE', 'R²'],
    'Baseline': [models_metrics['Baseline']['MSE'], models_metrics['Baseline']['RMSE'],
                 models_metrics['Baseline']['MAE'], models_metrics['Baseline']['R²']],
    'Random_Search': [models_metrics['Random_Search']['MSE'], models_metrics['Random_Search']['RMSE'],
                      models_metrics['Random_Search']['MAE'], models_metrics['Random_Search']['R²']]
}).round(4)

print("\n=== METRIC COMPARISON ===")
print(metrics_df.to_string(index=False))

# Improvement over baseline
improvement_data = []
for metric in ['MSE', 'RMSE', 'MAE', 'R²']:
    base = models_metrics['Baseline'][metric]
    rnd = models_metrics['Random_Search'][metric]
    if metric == 'R²':
        improvement = (rnd - base) / abs(base) * 100 if base != 0 else float('inf')
    else:
        improvement = (base - rnd) / base * 100
    improvement_data.append(improvement)

improvement_df = pd.DataFrame({
    'Method': ['Random_Search'],
    'MSE_Improvement_%': [improvement_data[0]],
    'RMSE_Improvement_%': [improvement_data[1]],
    'MAE_Improvement_%': [improvement_data[2]],
    'R²_Improvement_%': [improvement_data[3]]
}).round(2)

print("\n=== IMPROVEMENT OVER BASELINE (%) ===")
print(improvement_df.to_string(index=False))

# Training time
timing_df = pd.DataFrame({
    'Method': ['Random_Search'],
    'Time_Minutes': [(end_random - start_random) / 60]
}).round(2)

print("\n=== TRAINING TIME ===")
print(timing_df.to_string(index=False))

# Best model
best_method = 'Random_Search' if models_metrics['Random_Search']['RMSE'] < models_metrics['Baseline']['RMSE'] else 'Baseline'
best_rmse = min(models_metrics['Random_Search']['RMSE'], models_metrics['Baseline']['RMSE'])

print(f"\n=== BEST MODEL ===")
print(f"Method: {best_method}")
print(f"Best RMSE: {best_rmse:.4f}")

# Visual comparison
methods = ['Baseline', 'Random_Search']
metrics_to_plot = ['MSE', 'RMSE', 'MAE']

fig, axes = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle('Baseline vs Random Search Performance', fontsize=16)

for idx, metric in enumerate(metrics_to_plot):
    row, col = divmod(idx, 2)
    values = [models_metrics[method][metric] for method in methods]
    bars = axes[row, col].bar(methods, values, alpha=0.7)
    axes[row, col].set_title(f'{metric} Comparison')
    axes[row, col].set_ylabel(metric)

    best_idx = np.argmin(values)
    bars[best_idx].set_color('green')

# R² Comparison
r2_values = [models_metrics[method]['R²'] for method in methods]
bars = axes[1, 1].bar(methods, r2_values, alpha=0.7)
axes[1, 1].set_title('R² Comparison')
axes[1, 1].set_ylabel('R²')

best_r2_idx = np.argmax(r2_values)
bars[best_r2_idx].set_color('green')

plt.tight_layout()
plt.show()