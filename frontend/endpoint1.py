from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from typing import Optional
from datetime import datetime, timedelta
import pytz
from fastapi.responses import StreamingResponse
import io
import pandas as pd
from typing import Optional
from fastapi import Query
import numpy as np
from dateutil.relativedelta import relativedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from datetime import datetime
import os
import json

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to store the DataFrame
df = None

# def reload_data():
#     """Reload data from CSV file with proper datetime handling."""
#     global df
#     try:
#         # Load the CSV
#         df = pd.read_csv("parking_export.csv")
        
#         # Convert timestamp to datetime with error handling
#         try:
#             # First attempt: Try parsing as ISO format
#             df['datetime_utc'] = pd.to_datetime(df['timestamp'],format='ISO8601')
#         except (ValueError, TypeError) as e:
#             print(f"First parsing attempt failed: {e}")
#             try:
#                 # Second attempt: Try with explicit format
#                 df['datetime_utc'] = pd.to_datetime(df['timestamp'], format="%Y-%m-%d %H:%M:%S.%f%z")
#             except (ValueError, TypeError) as e:
#                 print(f"Second parsing attempt failed: {e}")
#                 # Final attempt: Try with coerce option to handle mixed formats
#                 df['datetime_utc'] = pd.to_datetime(df['timestamp'], format='mixed', utc=True)
        
#         # Verify the conversion worked
#         if not pd.api.types.is_datetime64_any_dtype(df['datetime_utc']):
#             print("Warning: datetime conversion did not result in datetime type")
#             # Force UTC timezone if not present
#             df['datetime_utc'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC')
        
#         return df
#     except Exception as e:
#         print(f"Error in reload_data: {e}")
#         raise


def reload_data():
    """Reload data from CSV file with proper datetime handling."""
    global df
    try:
        # Load the CSV
        df = pd.read_csv("parking_export.csv")
        
        # Convert timestamp to datetime; let pandas infer the format automatically
        df['datetime_utc'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
        
        # Verify the conversion worked
        if not pd.api.types.is_datetime64_any_dtype(df['datetime_utc']):
            print("Warning: datetime conversion did not result in datetime type")
            df['datetime_utc'] = pd.to_datetime(df['timestamp'], errors='coerce').dt.tz_localize('UTC')
        
        return df
    except Exception as e:
        print(f"Error in reload_data: {e}")
        raise


def safe_serialize(obj):
    """
    Custom JSON serializer to handle various data types.
    """
    if pd.isna(obj):
        return None
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def merge_entries_exits(df):
    """
    Optimized merge of entry and exit records with robust null handling.
    The fix here is to rename left-side columns (with _entry suffix) to their original names,
    ensuring that columns like 'category', 'color', 'zone', and 'description' are present.
    """
    # Convert timestamp and handle invalid dates
    df['datetime_utc'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    df = df.dropna(subset=['datetime_utc'])
    
    # Separate entries and exits based on the gate suffix
    mask_in = df['gate'].str.endswith('_in', na=False)
    mask_out = df['gate'].str.endswith('_out', na=False)
    
    entries = df[mask_in].copy()
    exits = df[mask_out].copy()
    
    # Rename the exit timestamp so it isn't used as the join key on both sides
    exits = exits.rename(columns={'datetime_utc': 'exit_timestamp'})
    
    # Sort for merge_asof
    entries = entries.sort_values('datetime_utc')
    exits = exits.sort_values('exit_timestamp')
    
    # Handle cases where there are no exit records.
    if entries.empty:
        return pd.DataFrame()  # or return an empty DataFrame with expected columns
    if exits.empty:
        entries['exit_timestamp'] = pd.NaT
        entries['exit_gate'] = ''
        entries['insertion_id_exit'] = -1
        entries['duration'] = -1
        result = entries.rename(columns={
            'datetime_utc': 'entry_timestamp',
            'gate': 'entry_gate',
            'insertion_id': 'insertion_id'
        })
        result = result[['insertion_id', 'license_plate', 'category', 'color',
                         'entry_timestamp', 'entry_gate', 'exit_timestamp', 'exit_gate',
                         'zone', 'description', 'insertion_id_exit', 'duration']]
        return result
    
    # Merge using merge_asof
    merged = pd.merge_asof(
        left=entries,
        right=exits,
        left_on='datetime_utc',
        right_on='exit_timestamp',
        by='license_plate',
        direction='forward',
        suffixes=('_entry', '_exit'),
        tolerance=pd.Timedelta(days=7)  # maximum allowed gap between entry and exit
    )
    
    # Calculate duration in seconds if an exit is found; else set to -1
    merged['duration'] = merged.apply(
        lambda x: (x['exit_timestamp'] - x['datetime_utc']).total_seconds() 
                  if pd.notnull(x['exit_timestamp']) else -1,
        axis=1
    )
    
    # Rename left-side columns to their desired final names.
    # This ensures that columns like 'category', 'color', 'zone', and 'description'
    # appear in the final DataFrame.
    merged = merged.rename(columns={
        'datetime_utc': 'entry_timestamp',
        'gate_entry': 'entry_gate',
        'insertion_id_entry': 'insertion_id',
        'category_entry': 'category',
        'color_entry': 'color',
        'zone_entry': 'zone',
        'description_entry': 'description'
    })
    
    # Select and order the desired columns.
    result_df = merged[['insertion_id', 'license_plate', 'category', 'color',
                        'entry_timestamp', 'entry_gate', 'exit_timestamp', 'gate_exit',
                        'zone', 'description', 'insertion_id_exit', 'duration']]
    result_df = result_df.rename(columns={'gate_exit': 'exit_gate'})
    
    # Fill null values as needed
    result_df['exit_timestamp'] = result_df['exit_timestamp'].fillna(pd.NaT)
    result_df['exit_gate'] = result_df['exit_gate'].fillna('')
    result_df['insertion_id_exit'] = result_df['insertion_id_exit'].fillna(-1)
    result_df['duration'] = result_df['duration'].fillna(-1)
    
    return result_df

@app.get("/data")
async def get_data(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    license_prefix: Optional[str] = None,
    category: Optional[str] = None,
    color: Optional[str] = None,
    gate: Optional[str] = None
):
    # Reload data
    reload_data()
    
    # Merge entries and exits using the optimized function.
    merged_df = merge_entries_exits(df)
    
    # Apply filters
    if search:
        string_cols = merged_df.select_dtypes(include=['object']).columns
        filter_cond = merged_df[string_cols].apply(
            lambda col: col.astype(str).str.contains(search, case=False, na=False)
        ).any(axis=1)
        merged_df = merged_df[filter_cond]
    
    # Date range filtering with robust parsing.
    try:
        if start_date or end_date:
            merged_df['parsed_entry_timestamp'] = pd.to_datetime(
                merged_df['entry_timestamp'], utc=True, errors='coerce'
            )
            if start_date:
                start = pd.to_datetime(start_date, utc=True)
                merged_df = merged_df[merged_df['parsed_entry_timestamp'] >= start]
            if end_date:
                end = pd.to_datetime(end_date, utc=True)
                merged_df = merged_df[merged_df['parsed_entry_timestamp'] <= end]
            merged_df = merged_df.drop(columns=['parsed_entry_timestamp'])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    
    # Additional filters
    if license_prefix:
        prefixes = license_prefix.split(',')
        merged_df = merged_df[merged_df['license_plate'].str.startswith(tuple(prefixes), na=False)]
    
    if category:
        merged_df = merged_df[merged_df['category'].isin(category.split(','))]
    
    if color:
        merged_df = merged_df[merged_df['color'].isin(color.split(','))]
    
    if gate:
        gates = gate.split(',')
        merged_df = merged_df[
            merged_df['entry_gate'].isin(gates) |
            merged_df['exit_gate'].isin(gates)
        ]
    
    # Sort and paginate.
    merged_df = merged_df.sort_values('entry_timestamp', ascending=False)
    total = len(merged_df)
    total_pages = (total + page_size - 1) // page_size
    paginated = merged_df.iloc[(page-1)*page_size : page*page_size]
    
    # Convert to list of dictionaries with safe serialization.
    data = paginated.apply(lambda row: {col: safe_serialize(val) for col, val in row.items()}, axis=1).tolist()
    
    return {
        "data": data,
        "total_pages": total_pages,
        "current_page": page,
        "total_records": total
    }




# Modify the existing /data endpoint
@app.get("/dashboard/data")
async def get_data(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
):
    reload_data()
    
    filtered_df = df.copy()
    
    # License plate prefix filter
    
    # Search filter
    if search:
        string_columns = df.select_dtypes(include=['object']).columns
        filter_conditions = []
        for column in string_columns:
            filter_conditions.append(df[column].astype(str).str.contains(search, case=False, na=False))
        filtered_df = df[pd.concat(filter_conditions, axis=1).any(axis=1)]
    
    # Date range filter
    # Sorting and pagination
    filtered_df = filtered_df.sort_values(by='timestamp', ascending=False)
    total_records = len(filtered_df)
    total_pages = (total_records + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    paginated_df = filtered_df.iloc[start_idx:end_idx]
    
    return {
        "data": paginated_df.to_dict(orient="records"),
        "total_records": total_records,
        "total_pages": total_pages,
        "current_page": page
    }

# @app.get("/stats/category-stats")
# async def get_category_stats(
#     start_date: Optional[str] = None,
#     end_date: Optional[str] = None
# ):
#     try:
#         reload_data()
        
#         filtered_df = df.copy()
        
#         # Handle date filtering only if dates are provided
#         if start_date or end_date:
#             if 'datetime_utc' not in filtered_df.columns:
#                 filtered_df['datetime_utc'] = pd.to_datetime(filtered_df['timestamp'], utc=True)
            
#             if start_date:
#                 start = pd.to_datetime(start_date, utc=True)
#                 filtered_df = filtered_df[filtered_df['datetime_utc'] >= start]
#             if end_date:
#                 end = pd.to_datetime(end_date, utc=True)
#                 filtered_df = filtered_df[filtered_df['datetime_utc'] <= end]
        
#         # Handle empty DataFrame
#         if filtered_df.empty:
#             return {"category_counts": {}}
        
#         # Count by category
#         category_counts = filtered_df['category'].value_counts().to_dict()
        
#         return {"category_counts": category_counts}
    
#     except Exception as e:
#         print(f"Error in category-stats: {str(e)}")
#         return {"error": str(e)}, 500
@app.get("/stats/category-stats")
async def get_category_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    # Detailed logging and error handling
    print("Received parameters:")
    print(f"start_date: {start_date}")
    print(f"end_date: {end_date}")
    
    reload_data()
    
    # Ensure datetime column exists
    if 'datetime_utc' not in df.columns:
        try:
            print("Converting timestamp to datetime")
            df['datetime_utc'] = pd.to_datetime(df['timestamp'], utc=True)
            print("Conversion successful")
        except Exception as conversion_error:
            print(f"Datetime conversion error: {conversion_error}")
            print("Sample timestamps:")
            print(df['timestamp'].head())
            return {"error": f"Could not convert timestamps: {conversion_error}"}, 500
    
    filtered_df = df.copy()
    
    # Date filtering with extensive error handling
    try:
        if start_date:
            print(f"Parsing start date: {start_date}")
            start = pd.to_datetime(start_date)
            print(f"Parsed start date: {start}")
            filtered_df = filtered_df[filtered_df['datetime_utc'].dt.date >= start.date()]
            print("Start date filtering applied")
        
        if end_date:
            print(f"Parsing end date: {end_date}")
            end = pd.to_datetime(end_date)
            print(f"Parsed end date: {end}")
            filtered_df = filtered_df[filtered_df['datetime_utc'].dt.date <= end.date()]
            print("End date filtering applied")
    
    except Exception as date_error:
        print(f"Date filtering error: {date_error}")
        print("Timestamps:")
        print(filtered_df['timestamp'].head())
        print("Datetime UTC:")
        print(filtered_df['datetime_utc'].head())
        return {"error": f"Date filtering failed: {date_error}"}, 400
    
    # Handle empty DataFrame
    if filtered_df.empty:
        print("Filtered DataFrame is empty")
        return {"category_counts": {}}
    
    # Count by category
    category_counts = filtered_df['category'].value_counts().to_dict()
    
    print(f"Category counts: {category_counts}")
    return {"category_counts": category_counts}


def calculate_percentage_changes(current_counts, previous_counts):
    changes = {}
    for category, current in current_counts.items():
        previous = previous_counts.get(category, 0)
        if previous == 0:
            changes[category] = 100.0 if current > 0 else 0.0
        else:
            changes[category] = round(((current - previous) / previous) * 100, 1)
    return changes

@app.get("/stats/enhanced-stats")
async def get_enhanced_stats(
    start_date: Optional[str] = Query(None, description="Start date (ISO 8601 format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO 8601 format)"),
    time_range: Optional[str] = Query('all', enum=['today', 'week', 'month', 'custom'])
):
    reload_data()
    
    # Get current time (UTC) with timezone awareness
    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    
    # Set start_date and end_date based on the selected time_range
    if time_range != 'custom':
        if time_range == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif time_range == 'week':
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif time_range == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        else:  # all time
            start_date = df['datetime_utc'].min()
            end_date = df['datetime_utc'].max()

    # If provided as strings, convert start_date and end_date to datetime objects
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date, utc=True)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date, utc=True)
    
    # Filter the DataFrame based on the datetime_utc column
    mask = (df['datetime_utc'] >= start_date) & (df['datetime_utc'] <= end_date)
    filtered_df = df.loc[mask].copy()  # Use .copy() to avoid potential warnings
    
    # Ensure the datetime_utc column is of datetime type and sorted
    filtered_df['datetime_utc'] = pd.to_datetime(filtered_df['datetime_utc'], utc=True)
    filtered_df.sort_values('datetime_utc', inplace=True)
    
    # Use groupby with pd.Grouper for zone activity timeline
    zone_activity_timeline = (
        filtered_df
        .groupby(pd.Grouper(key='datetime_utc', freq='H'))
        .size()
        .reset_index(name='activity')
        .rename(columns={'datetime_utc': 'time'})
        .to_dict('records')
    )
    
    stats = {}
    # Add new stats calculations
    entry_exit_by_category = (
        filtered_df
        .assign(entry_type=lambda df: df['gate'].str.contains('_in').map({True: 'entry', False: 'exit'}))
        .groupby(['category', 'entry_type'])
        .size()
        .unstack(fill_value=0)
        .to_dict(orient='index')
    )

    daily_trend = (
    filtered_df
    .set_index('datetime_utc')
    .resample('D')
    .size()
    .to_dict()
)

    heatmap_data = (
        filtered_df
        .assign(
            hour=filtered_df['datetime_utc'].dt.hour,
            day_of_week=filtered_df['datetime_utc'].dt.dayofweek
        )
        .groupby(['day_of_week', 'hour'])
        .size()
        .reset_index(name='count')
        .to_dict(orient='records')
    )

    prev_start_date, prev_end_date = calculate_previous_period(start_date, end_date, time_range)
    
    # Fetch previous period data
    prev_mask = (df['datetime_utc'] >= prev_start_date) & (df['datetime_utc'] <= prev_end_date)
    prev_filtered_df = df.loc[prev_mask].copy()
    
    # Calculate counts
    current_counts = filtered_df['category'].value_counts().to_dict()
    previous_counts = prev_filtered_df['category'].value_counts().to_dict()
    
    # Calculate percentage changes
    percentage_changes = calculate_percentage_changes(current_counts, previous_counts)

    # Build the stats dictionary
    stats = {
        "entry_exit_counts": {
            "entry": filtered_df[filtered_df['gate'].str.contains('_in', case=False)].shape[0],
            "exit": filtered_df[filtered_df['gate'].str.contains('_out', case=False)].shape[0]
        },
        "zone_activity_timeline": zone_activity_timeline,
        "total_events": len(filtered_df),
        "busiest_hour": int(filtered_df['datetime_utc'].dt.hour.mode()[0]) if not filtered_df.empty else None,
        "category_counts": filtered_df['category'].value_counts().to_dict(),
        "gate_usage": filtered_df['gate'].value_counts().to_dict(),
        # If you still want to use resample for hourly_trend, ensure the index is set to datetime:
        "hourly_trend": {
            str(ts): count 
            for ts, count in filtered_df.set_index('datetime_utc').resample('H').size().items()
        },
        "color_distribution": filtered_df['color'].value_counts().to_dict(),
        "zone_counts": filtered_df['zone'].value_counts().to_dict()
    }
    
    stats.update({
        "entry_exit_by_category": entry_exit_by_category,
        "daily_trend": daily_trend,
        "heatmap_data": heatmap_data
    })
    
    return {
        "stats": stats,
        "percentage_changes": percentage_changes
    }
    
    
    
def calculate_previous_period(start_date, end_date, time_range):
    if time_range == 'today':
        delta = end_date - start_date
        return start_date - delta, end_date - delta
    elif time_range == 'week':
        return start_date - timedelta(weeks=1), end_date - timedelta(weeks=1)
    elif time_range == 'month':
        return start_date - relativedelta(months=1), end_date - relativedelta(months=1)
    else:  # custom
        delta = end_date - start_date
        return start_date - delta, end_date - delta

@app.get("/stats/today")
async def get_today_count():
    reload_data()
    today_utc = datetime.now(pytz.utc).date()
    
    if pd.api.types.is_datetime64_any_dtype(df['datetime_utc']):
        today_df = df[df['datetime_utc'].dt.date == today_utc]
    else:
        # Fallback if datetime conversion failed
        print("Warning: Using timestamp string comparison for today's count")
        today_str = today_utc.strftime('%Y-%m-%d')
        today_df = df[df['timestamp'].str.startswith(today_str)]
    
    return {"count": len(today_df)}




@app.get("/stats/recent-entries")
async def get_recent_entries():
    reload_data()
    ten_minutes_ago = datetime.now(pytz.utc) - timedelta(minutes=10)
    
    if pd.api.types.is_datetime64_any_dtype(df['datetime_utc']):
        recent_entries = df[
            (df['datetime_utc'] >= ten_minutes_ago) &
            (df['gate'].str.contains('_in'))
        ]
    else:
        # Fallback if datetime conversion failed
        print("Warning: Using timestamp string comparison for recent entries")
        recent_entries = df[df['gate'].str.contains('_in')]
    
    return {"count": len(recent_entries)}

@app.get("/stats/recent-exits")
async def get_recent_exits():
    reload_data()
    ten_minutes_ago = datetime.now(pytz.utc) - timedelta(minutes=10)
    
    if pd.api.types.is_datetime64_any_dtype(df['datetime_utc']):
        recent_exits = df[
            (df['datetime_utc'] >= ten_minutes_ago) &
            (df['gate'].str.contains('_out'))
        ]
    else:
        # Fallback if datetime conversion failed
        print("Warning: Using timestamp string comparison for recent exits")
        recent_exits = df[df['gate'].str.contains('_out')]
    
    return {"count": len(recent_exits)}


@app.get("/categories")
async def get_categories():
    reload_data()
    categories = df['category'].dropna().unique().tolist()
    return {"categories": categories}

@app.get("/colors")
async def get_colors():
    reload_data()
    colors = df['color'].dropna().unique().tolist()
    return {"colors": colors}

@app.get("/gates")
async def get_gates():
    reload_data()
    gates = df['gate'].dropna().unique().tolist()
    return {"gates": gates}

@app.get("/filters/categories")
async def get_categories_filter():
    """New endpoint to match frontend expectations"""
    reload_data()
    categories = df['category'].dropna().unique().tolist()
    return {"categories": categories}

@app.get("/filters/colors")
async def get_colors_filter():
    """New endpoint to match frontend expectations"""
    reload_data()
    colors = df['color'].dropna().unique().tolist()
    return {"colors": colors}

@app.get("/filters/gates")
async def get_gates_filter():
    """Endpoint to get raw gate names from CSV"""
    reload_data()
    gates = df['gate'].dropna().unique().tolist()
    return {"gates": gates}

@app.get("/export")
async def export_data(
    file_format: str = Query(..., regex="^(csv|xlsx)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    license_prefix: Optional[str] = None,
    categories: Optional[str] = None,
    colors: Optional[str] = None,
    gates: Optional[str] = None,
    search: Optional[str] = None
):
    reload_data()
    filtered_df = df.copy()
    
    # Apply filters
    if license_prefix:
        prefix_list = license_prefix.split(',')
        mask = filtered_df['license_plate'].str[:2].isin(prefix_list)
        filtered_df = filtered_df[mask]
    
    if categories:
        category_list = categories.split(',')
        filtered_df = filtered_df[filtered_df['category'].isin(category_list)]
    
    if colors:
        color_list = colors.split(',')
        filtered_df = filtered_df[filtered_df['color'].isin(color_list)]
    
    if gates:
        gate_list = gates.split(',')
        filtered_df = filtered_df[filtered_df['gate'].isin(gate_list)]
    
    if search:
        string_columns = filtered_df.select_dtypes(include=['object']).columns
        filter_conditions = []
        for column in string_columns:
            filter_conditions.append(filtered_df[column].astype(str).str.contains(search, case=False, na=False))
        filtered_df = filtered_df[pd.concat(filter_conditions, axis=1).any(axis=1)]
    
    # Handle datetime conversion
    if 'timestamp' in filtered_df.columns:
        if pd.api.types.is_datetime64_any_dtype(filtered_df['timestamp']):
            # The column is already datetime, so just remove the timezone
            filtered_df['timestamp'] = filtered_df['timestamp'].dt.tz_localize(None)
        else:
            # Parse the column as datetime (allowing mixed formats) and remove timezone
            filtered_df['timestamp'] = pd.to_datetime(
                filtered_df['timestamp'],
                utc=True,
                errors='coerce'
            ).dt.tz_localize(None)
    
    # Date range filtering
    if start_date or end_date:
        if start_date:
            start = pd.to_datetime(start_date)
            filtered_df = filtered_df[filtered_df['timestamp'] >= start]
        if end_date:
            end = pd.to_datetime(end_date)
            filtered_df = filtered_df[filtered_df['timestamp'] <= end]
    
    # Create buffer for file
    buffer = io.BytesIO()
    
    # Export based on format
    if file_format == 'csv':
        filtered_df.to_csv(buffer, index=False)
        media_type = 'text/csv'
        filename = 'export.csv'
    else:  # xlsx
        # Ensure all datetime columns are timezone-naive
        for column in filtered_df.select_dtypes(include=['datetime64[ns, UTC]']).columns:
            filtered_df[column] = filtered_df[column].dt.tz_localize(None)
        
        filtered_df.to_excel(buffer, index=False, engine='openpyxl')
        media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = 'export.xlsx'
    
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={
            'Content-Disposition': f'attachment; filename={filename}',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
    )

@app.get("/stats/today-entries")
async def get_today_entries():
    reload_data()
    today_utc = datetime.now(pytz.utc).date()
    
    if pd.api.types.is_datetime64_any_dtype(df['datetime_utc']):
        today_entries = df[
            (df['datetime_utc'].dt.date == today_utc) &
            (df['gate'].str.contains('_in'))
        ]
    else:
        today_str = today_utc.strftime('%Y-%m-%d')
        today_entries = df[
            (df['timestamp'].str.startswith(today_str)) &
            (df['gate'].str.contains('_in'))
        ]
    
    return {"count": len(today_entries)}

@app.get("/stats/today-exits")
async def get_today_exits():
    reload_data()
    today_utc = datetime.now(pytz.utc).date()
    
    if pd.api.types.is_datetime64_any_dtype(df['datetime_utc']):
        today_exits = df[
            (df['datetime_utc'].dt.date == today_utc) &
            (df['gate'].str.contains('_out'))
        ]
    else:
        today_str = today_utc.strftime('%Y-%m-%d')
        today_exits = df[
            (df['timestamp'].str.startswith(today_str)) &
            (df['gate'].str.contains('_out'))
        ]
    
    return {"count": len(today_exits)}



@app.get("/export-logs")
async def get_export_logs():
    try:
        with open("export_logs.json", "r") as f:
            logs = json.load(f)
        return logs
    except FileNotFoundError:
        return []

@app.post("/log-export")
async def log_export(export_data: dict):
    try:
        # Read existing logs
        try:
            with open("export_logs.json", "r") as f:
                logs = json.load(f)
        except FileNotFoundError:
            logs = []

        # Add new log entry
        new_log = {
            "id": len(logs) + 1,
            "fileName": export_data["fileName"],
            "format": export_data["format"],
            "timestamp": datetime.now().isoformat(),
            "recordCount": export_data["recordCount"],
            "exportType": export_data["exportType"],
            "filters": export_data["filters"]
        }
        
        logs.append(new_log)

        # Save updated logs
        with open("export_logs.json", "w") as f:
            json.dump(logs, f)

        return new_log
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download-export/{export_id}")
async def download_export(export_id: int):
    try:
        # Read logs to get export details
        with open("export_logs.json", "r") as f:
            logs = json.load(f)
        
        log_entry = next((log for log in logs if log["id"] == export_id), None)
        if not log_entry:
            raise HTTPException(status_code=404, detail="Export not found")

        # Get the exported file path
        file_path = f"exports/{log_entry['fileName']}{log_entry['format']}"
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Export file not found")

        return FileResponse(
            file_path,
            filename=f"{log_entry['fileName']}{log_entry['format']}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/duration-stats")
async def get_duration_stats(
    time_range: str = Query("today", description="Time range for stats"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    reload_data()
    
    # Get merged data with durations
    merged_df = merge_entries_exits(df)
    
    # Convert timestamps to datetime if they're strings
    if start_date:
        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    if end_date:
        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

    # Filter data based on time range
    now = datetime.now(pytz.UTC)
    
    if time_range == "custom" and start_date and end_date:
        current_data = merged_df[
            (merged_df['entry_timestamp'] >= start_date) & 
            (merged_df['entry_timestamp'] <= end_date)
        ]
        # Calculate previous period
        period_length = end_date - start_date
        previous_start = start_date - period_length
        previous_end = start_date
        previous_data = merged_df[
            (merged_df['entry_timestamp'] >= previous_start) & 
            (merged_df['entry_timestamp'] <= previous_end)
        ]
    else:
        if time_range == "today":
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            previous_start = start_time - timedelta(days=1)
        elif time_range == "week":
            start_time = now - timedelta(days=7)
            previous_start = start_time - timedelta(days=7)
        elif time_range == "month":
            start_time = now - timedelta(days=30)
            previous_start = start_time - timedelta(days=30)
        else:  # Default to today
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            previous_start = start_time - timedelta(days=1)

        current_data = merged_df[merged_df['entry_timestamp'] >= start_time]
        previous_data = merged_df[
            (merged_df['entry_timestamp'] >= previous_start) & 
            (merged_df['entry_timestamp'] < start_time)
        ]

    # Calculate averages with proper duration calculation
    def calculate_average_duration(data):
        if data.empty:
            return 0
            
        # Calculate duration for each entry-exit pair
        durations = []
        for _, row in data.iterrows():
            if pd.notna(row['entry_timestamp']) and pd.notna(row['exit_timestamp']):
                duration = (row['exit_timestamp'] - row['entry_timestamp']).total_seconds()
                if duration > 0:  # Only include valid durations
                    durations.append(duration)
        
        # Calculate average if we have valid durations
        return sum(durations) / len(durations) if durations else 0

    current_avg = calculate_average_duration(current_data)
    previous_avg = calculate_average_duration(previous_data)

    # Calculate percentage change
    def calculate_percentage_change(current, previous):
        if previous == 0:
            return 0
        return ((current - previous) / previous) * 100

    percentage_change = calculate_percentage_change(current_avg, previous_avg)

    return {
        "average_duration": round(current_avg) if not pd.isna(current_avg) else 0,
        "previous_average": round(previous_avg) if not pd.isna(previous_avg) else 0,
        "percentage_change": round(percentage_change, 2),
        "time_range": time_range
    }

@app.get("/stats/trends")
async def get_trends():
    reload_data()
    
    # Get today's date in UTC
    today = datetime.now(pytz.utc).date()
    yesterday = today - timedelta(days=1)
    
    # Calculate today's counts
    today_entries = df[
        (df['datetime_utc'].dt.date == today) &
        (df['gate'].str.contains('_in'))
    ].shape[0]
    
    today_exits = df[
        (df['datetime_utc'].dt.date == today) &
        (df['gate'].str.contains('_out'))
    ].shape[0]
    
    # Calculate yesterday's counts
    yesterday_entries = df[
        (df['datetime_utc'].dt.date == yesterday) &
        (df['gate'].str.contains('_in'))
    ].shape[0]
    
    yesterday_exits = df[
        (df['datetime_utc'].dt.date == yesterday) &
        (df['gate'].str.contains('_out'))
    ].shape[0]
    
    # Calculate percentage changes
    def calculate_trend(current, previous):
        if previous == 0:
            return "+100%" if current > 0 else "0%"
        change = ((current - previous) / previous) * 100
        return f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
    
    # Calculate total traffic trends
    total_today = today_entries + today_exits
    total_yesterday = yesterday_entries + yesterday_exits
    
    return {
        "entry_trend": calculate_trend(today_entries, yesterday_entries),
        "exit_trend": calculate_trend(today_exits, yesterday_exits),
        "total_trend": calculate_trend(total_today, total_yesterday)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)