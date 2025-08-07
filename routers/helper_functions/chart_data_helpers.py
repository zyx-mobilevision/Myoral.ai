from datetime import datetime, timedelta
import numpy as np


def generate_chart_data(user_info=None, caries_history=None, recession_history=None):
    """
    Generate chart data for frontend plotting.
    
    Args:
        user_info: User information dictionary
        caries_history: Dictionary with date keys and caries count values
        recession_history: Dictionary with date keys and recession count values
    
    Returns:
        Dictionary containing chart data for all three charts
    """
    chart_data = {
        "caries_chart": None,
        "recession_chart": None,
        "gum_inflammation_chart": None
    }
    
    # Generate Caries Chart Data
    if caries_history:
        caries_items = sorted(caries_history.items(), key=lambda x: x[0])
        caries_data = [{"date": date, "count": count} for date, count in caries_items]
        
        # Calculate age-based comparison
        caries_age_map = {
            (5, 14): 0.8,
            (15, 24): 2.1,
            (25, 34): 3.2,
            (35, 44): 5.0,
            (45, 54): 7.2,
            (55, 64): 10.1,
            (65, 74): 13.2,
            (75, 120): 15.0
        }
        
        age_group = "(25,34)"
        avg_caries_val = 3.2
        
        if user_info and user_info.get("Birthdate"):
            try:
                birth = user_info["Birthdate"]
                if isinstance(birth, str):
                    birth = birth[:10]
                birthdate = datetime.strptime(str(birth), "%Y-%m-%d")
                today = datetime.utcnow() + timedelta(hours=8)
                user_age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
                
                for (a, b), val in caries_age_map.items():
                    if a <= user_age <= b:
                        age_group = f"({a},{b})"
                        avg_caries_val = val
                        break
            except Exception:
                avg_caries_val = 3.2
        
        # Calculate comparison
        caries_vals = [item["count"] for item in caries_data]
        latest_count = caries_vals[-1] if caries_vals else 0
        comparison_text = "--"
        
        if caries_vals and avg_caries_val > 0:
            percent_diff = (latest_count - avg_caries_val) / avg_caries_val * 100
            if percent_diff > 0:
                comparison_text = f"Attention! Worse than the average by {percent_diff:.1f}%"
            elif percent_diff < 0:
                comparison_text = f"Good! Better than the average by {abs(percent_diff):.1f}%"
            else:
                comparison_text = "Same as the average"
        
        chart_data["caries_chart"] = {
            "data": caries_data,
            "metadata": {
                "user_age_group": age_group,
                "average_for_age": avg_caries_val,
                "latest_count": latest_count,
                "comparison_text": comparison_text
            }
        }
    
    # Generate Recession Chart Data
    if recession_history:
        recession_items = sorted(recession_history.items(), key=lambda x: x[0])
        recession_data = [{"date": date, "count": count} for date, count in recession_items]
        
        # Calculate averages
        recession_vals = [item["count"] for item in recession_data]
        user_average = np.mean(recession_vals) if recession_vals else 0
        others_average = 1.2  # Fixed baseline as in PDF
        
        # Calculate comparison
        comparison_text = "--"
        if recession_vals:
            if user_average > others_average:
                percent_diff = (user_average - others_average) / others_average * 100
                comparison_text = f"Attention! Higher than the average by {percent_diff:.1f}% (User: {user_average:.2f}, Avg: {others_average})"
            elif user_average < others_average:
                percent_diff = (others_average - user_average) / others_average * 100
                comparison_text = f"Good! Lower than the average by {percent_diff:.1f}% (User: {user_average:.2f}, Avg: {others_average})"
            else:
                comparison_text = f"Same as the average (User: {user_average:.2f}, Avg: {others_average})"
        
        chart_data["recession_chart"] = {
            "data": recession_data,
            "metadata": {
                "user_average": round(user_average, 2),
                "others_average": others_average,
                "comparison_text": comparison_text
            }
        }
    
    # Generate Gum Inflammation Chart Data (using mock data as in PDF)
    # Note: This uses hardcoded data as the original PDF implementation
    gum_dates = [
        "2025-06-15", "2025-06-22", "2025-06-29", "2025-07-06", "2025-07-13", 
        "2025-07-20", "2025-07-22", "2025-07-25", "2025-07-27", "2025-07-29"
    ]
    gum_vals = [78, 82, 85, 80, 88, 90, 83, 87, 85, 84]
    
    gum_data = [{"date": date, "score": score} for date, score in zip(gum_dates, gum_vals)]
    
    # Calculate comparison
    user_average = int(round(sum(gum_vals) / len(gum_vals)))
    others_average = 83
    
    comparison_text = "--"
    if user_average > others_average:
        percent_diff = (user_average - others_average) / others_average * 100
        comparison_text = f"Good! Higher than the average by {percent_diff:.1f}% (User: {user_average}, Avg: {others_average})"
    elif user_average < others_average:
        percent_diff = (others_average - user_average) / others_average * 100
        comparison_text = f"Attention! Lower than the average by {percent_diff:.1f}% (User: {user_average}, Avg: {others_average})"
    else:
        comparison_text = f"Same as the average (User: {user_average}, Avg: {others_average})"
    
    chart_data["gum_inflammation_chart"] = {
        "data": gum_data,
        "metadata": {
            "user_average": user_average,
            "others_average": others_average,
            "comparison_text": comparison_text,
            "note": "This chart uses demo data - replace with real gum inflammation tracking when available"
        }
    }
    
    return chart_data
