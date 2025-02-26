from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import Optional
import pytz
import asyncpg
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
import io
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
import os
import json
import logging

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DATABASE_URL = "postgresql://user:password@localhost/dbname"
pool = None

async def get_db():
    return await asyncpg.create_pool(DATABASE_URL)

@app.on_event("startup")
async def startup():
    global pool
    pool = await get_db()

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

async def fetch(query, *args):
    async with pool.acquire() as connection:
        return await connection.fetch(query, *args)

async def execute(query, *args):
    async with pool.acquire() as connection:
        return await connection.execute(query, *args)

# Modified merge_entries_exits using SQL
async def merge_entries_exits():
    query = """
    WITH entries AS (
        SELECT 
            insertion_id, license_plate, category, color, zone, description,
            timestamp as entry_timestamp,
            gate as entry_gate
        FROM parking_data
        WHERE gate LIKE '%_in'
    ),
    exits AS (
        SELECT 
            insertion_id as exit_insertion_id,
            timestamp as exit_timestamp,
            gate as exit_gate
        FROM parking_data
        WHERE gate LIKE '%_out'
    )
    SELECT 
        e.insertion_id, e.license_plate, e.category, e.color,
        e.entry_timestamp, e.entry_gate,
        ex.exit_timestamp, ex.exit_gate,
        e.zone, e.description,
        ex.exit_insertion_id,
        EXTRACT(EPOCH FROM (ex.exit_timestamp - e.entry_timestamp)) as duration
    FROM entries e
    LEFT JOIN LATERAL (
        SELECT *
        FROM exits ex
        WHERE ex.exit_timestamp >= e.entry_timestamp
        AND ex.license_plate = e.license_plate
        ORDER BY ex.exit_timestamp
        LIMIT 1
    ) ex ON true
    """
    return await fetch(query)

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
    base_query = """
    SELECT * FROM (
        SELECT 
            insertion_id, license_plate, category, color,
            entry_timestamp, entry_gate,
            exit_timestamp, exit_gate,
            zone, description,
            exit_insertion_id, duration
        FROM merged_entries_exits
    ) as data
    """
    
    where_clauses = []
    params = []
    
    # Add filters
    if search:
        where_clauses.append("""
            (license_plate ILIKE $1 OR 
            category::text ILIKE $1 OR 
            color::text ILIKE $1 OR 
            zone::text ILIKE $1 OR 
            description::text ILIKE $1)
        """)
        params.append(f"%{search}%")
    
    if start_date:
        where_clauses.append("entry_timestamp >= $%d" % (len(params)+1))
        params.append(start_date)
    
    if end_date:
        where_clauses.append("entry_timestamp <= $%d" % (len(params)+1))
        params.append(end_date)
    
    if license_prefix:
        prefixes = license_prefix.split(',')
        where_clauses.append("license_plate SIMILAR TO $%d" % (len(params)+1))
        params.append(f"({'|'.join(prefixes)})%")
    
    if category:
        categories = category.split(',')
        where_clauses.append("category = ANY($%d)" % (len(params)+1))
        params.append(categories)
    
    if color:
        colors = color.split(',')
        where_clauses.append("color = ANY($%d)" % (len(params)+1))
        params.append(colors)
    
    if gate:
        gates = gate.split(',')
        where_clauses.append("(entry_gate = ANY($%d) OR exit_gate = ANY($%d))" % (len(params)+1, len(params)+1))
        params.append(gates)
        params.append(gates)
    
    # Build final query
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
    
    # Add pagination
    base_query += f" ORDER BY entry_timestamp DESC LIMIT {page_size} OFFSET {(page-1)*page_size}"
    
    # Execute query
    try:
        data = await fetch(base_query, *params)
        count_query = "SELECT COUNT(*) FROM (" + base_query.replace(f"LIMIT {page_size} OFFSET {(page-1)*page_size}", "") + ") as total"
        total = await fetch(count_query, *params[:-2] if gate else params)
        total_records = total[0]['count'] if total else 0
        total_pages = (total_records + page_size - 1) // page_size
        
        return {
            "data": data,
            "total_pages": total_pages,
            "current_page": page,
            "total_records": total_records
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Similar modifications for other endpoints...

@app.get("/stats/category-stats")
async def get_category_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    query = """
    SELECT category, COUNT(*) as count
    FROM parking_data
    WHERE 1=1
    """
    params = []
    
    if start_date:
        query += " AND timestamp >= $%d" % (len(params)+1)
        params.append(start_date)
    if end_date:
        query += " AND timestamp <= $%d" % (len(params)+1)
        params.append(end_date)
    
    query += " GROUP BY category"
    
    try:
        result = await fetch(query, *params)
        return {"category_counts": {row['category']: row['count'] for row in result}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Other endpoints follow similar patterns...

@app.get("/dashboard/data")
async def get_dashboard_data(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None
):
    base_query = "SELECT * FROM parking_data"
    count_query = "SELECT COUNT(*) FROM parking_data"
    where_clauses = []
    params = []

    if search:
        where_clauses.append("""
            (license_plate ILIKE $1 OR 
            category::text ILIKE $1 OR 
            color::text ILIKE $1 OR 
            gate::text ILIKE $1)
        """)
        params.append(f"%{search}%")

    if where_clauses:
        where_stmt = " WHERE " + " AND ".join(where_clauses)
        base_query += where_stmt
        count_query += where_stmt

    # Pagination
    base_query += f" ORDER BY timestamp DESC LIMIT {page_size} OFFSET {(page-1)*page_size}"

    try:
        data = await fetch(base_query, *params)
        total = await fetch(count_query, *params)
        return {
            "data": data,
            "total_records": total[0]['count'],
            "total_pages": (total[0]['count'] + page_size - 1) // page_size,
            "current_page": page
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/enhanced-stats")
async def get_enhanced_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    time_range: str = Query('all', enum=['today', 'week', 'month', 'custom'])
):
    # Date handling
    time_conditions = {
        'today': "timestamp::date = CURRENT_DATE",
        'week': "timestamp >= DATE_TRUNC('week', CURRENT_DATE)",
        'month': "timestamp >= DATE_TRUNC('month', CURRENT_DATE)",
        'all': "1=1"
    }
    base_condition = time_conditions.get(time_range, "1=1")
    
    query = f"""
    WITH filtered_data AS (
        SELECT * 
        FROM parking_data
        WHERE {base_condition}
    ), entry_exit AS (
        SELECT
            category,
            CASE WHEN gate LIKE '%_in' THEN 'entry' ELSE 'exit' END as entry_type
        FROM filtered_data
    ), heatmap AS (
        SELECT
            EXTRACT(DOW FROM timestamp) as day_of_week,
            EXTRACT(HOUR FROM timestamp) as hour,
            COUNT(*) as count
        FROM filtered_data
        GROUP BY day_of_week, hour
    )
    SELECT
        (SELECT COUNT(*) FROM filtered_data WHERE gate LIKE '%_in') as entry_count,
        (SELECT COUNT(*) FROM filtered_data WHERE gate LIKE '%_out') as exit_count,
        (SELECT jsonb_object_agg(category, count) 
         FROM (SELECT category, COUNT(*) FROM filtered_data GROUP BY category) t) as category_counts,
        (SELECT jsonb_object_agg(gate, count) 
         FROM (SELECT gate, COUNT(*) FROM filtered_data GROUP BY gate) t) as gate_usage,
        (SELECT jsonb_agg(jsonb_build_object('day_of_week', day_of_week, 'hour', hour, 'count', count))
         FROM heatmap) as heatmap_data
    """
    
    try:
        result = await fetch(query)
        return {"stats": result[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/today")
async def get_today_count():
    query = """
    SELECT COUNT(*) as count 
    FROM parking_data 
    WHERE timestamp::date = CURRENT_DATE
    """
    result = await fetch(query)
    return {"count": result[0]['count']}

@app.get("/stats/recent-entries")
async def get_recent_entries():
    query = """
    SELECT COUNT(*) as count 
    FROM parking_data 
    WHERE gate LIKE '%_in' 
    AND timestamp >= NOW() - INTERVAL '10 minutes'
    """
    result = await fetch(query)
    return {"count": result[0]['count']}

@app.get("/stats/recent-exits")
async def get_recent_exits():
    query = """
    SELECT COUNT(*) as count 
    FROM parking_data 
    WHERE gate LIKE '%_out' 
    AND timestamp >= NOW() - INTERVAL '10 minutes'
    """
    result = await fetch(query)
    return {"count": result[0]['count']}

@app.get("/categories")
async def get_categories():
    result = await fetch("SELECT DISTINCT category FROM parking_data WHERE category IS NOT NULL")
    return {"categories": [r['category'] for r in result]}

@app.get("/colors")
async def get_colors():
    result = await fetch("SELECT DISTINCT color FROM parking_data WHERE color IS NOT NULL")
    return {"colors": [r['color'] for r in result]}

@app.get("/gates")
async def get_gates():
    result = await fetch("SELECT DISTINCT gate FROM parking_data WHERE gate IS NOT NULL")
    return {"gates": [r['gate'] for r in result]}

@app.get("/filters/categories")
async def get_categories_filter():
    result = await fetch("SELECT DISTINCT category FROM parking_data WHERE category IS NOT NULL")
    return {"categories": [r['category'] for r in result]}

@app.get("/filters/colors")
async def get_colors_filter():
    result = await fetch("SELECT DISTINCT color FROM parking_data WHERE color IS NOT NULL")
    return {"colors": [r['color'] for r in result]}

@app.get("/filters/gates")
async def get_gates_filter():
    result = await fetch("SELECT DISTINCT gate FROM parking_data WHERE gate IS NOT NULL")
    return {"gates": [r['gate'] for r in result]}

@app.get("/export")
async def export_data(
    file_format: str = Query(..., regex="^(csv|xlsx)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    query = "SELECT * FROM parking_data"
    params = []
    
    if start_date or end_date:
        conditions = []
        if start_date:
            conditions.append("timestamp >= $1")
            params.append(start_date)
        if end_date:
            conditions.append("timestamp <= $2")
            params.append(end_date)
        query += " WHERE " + " AND ".join(conditions)
    
    data = await fetch(query, *params)
    df = pd.DataFrame(data)

    buffer = io.BytesIO()
    if file_format == "csv":
        df.to_csv(buffer, index=False)
        media_type = "text/csv"
        filename = "export.csv"
    else:
        df.to_excel(buffer, index=False, engine="openpyxl")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "export.xlsx"
    
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/stats/duration-stats")
async def get_duration_stats():
    query = """
    SELECT 
        AVG(duration) as avg_duration,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration) as median_duration
    FROM merged_entries_exits
    WHERE duration > 0
    """
    result = await fetch(query)
    return {
        "average_duration": result[0]['avg_duration'],
        "median_duration": result[0]['median_duration']
    }

@app.get("/stats/trends")
async def get_trends():
    query = """
    WITH today_stats AS (
        SELECT
            COUNT(*) FILTER (WHERE gate LIKE '%_in') as today_entries,
            COUNT(*) FILTER (WHERE gate LIKE '%_out') as today_exits
        FROM parking_data
        WHERE timestamp::date = CURRENT_DATE
    ),
    yesterday_stats AS (
        SELECT
            COUNT(*) FILTER (WHERE gate LIKE '%_in') as yesterday_entries,
            COUNT(*) FILTER (WHERE gate LIKE '%_out') as yesterday_exits
        FROM parking_data
        WHERE timestamp::date = CURRENT_DATE - INTERVAL '1 day'
    )
    SELECT
        today_entries,
        today_exits,
        yesterday_entries,
        yesterday_exits
    FROM today_stats, yesterday_stats
    """
    result = await fetch(query)
    return {
        "entry_trend": f"{((result[0]['today_entries'] - result[0]['yesterday_entries'])/result[0]['yesterday_entries']*100 if result[0]['yesterday_entries'] else 0):.1f}%",
        "exit_trend": f"{((result[0]['today_exits'] - result[0]['yesterday_exits'])/result[0]['yesterday_exits']*100 if result[0]['yesterday_exits'] else 0):.1f}%"
    }

# ... [Keep the existing /export-logs, /log-export, and /download-export endpoints as they are file-based] ...

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 