# src/ingestion/aqi_calculator.py

def get_sub_index(conc, bp):
    """
    Calculate sub-index for a pollutant based on its concentration and breakpoints.
    bp is a list of tuples: (conc_lo, conc_hi, aqi_lo, aqi_hi)
    """
    for (c_low, c_high, i_low, i_high) in bp:
        if c_low <= conc <= c_high:
            return round(((i_high - i_low) / (c_high - c_low)) * (conc - c_low) + i_low)
    # If it exceeds the highest breakpoint, extrapolate using the highest tier
    c_low, c_high, i_low, i_high = bp[-1]
    return round(((i_high - i_low) / (c_high - c_low)) * (conc - c_low) + i_low)

def calculate_indian_aqi(pm25, pm10, no2, so2, co):
    """
    Calculates the Indian National Air Quality Index (AQI).
    Returns (aqi_value, dominant_pollutant).
    """
    # Breakpoints: (Conc Low, Conc High, AQI Low, AQI High)
    bp_pm25 = [(0, 30, 0, 50), (31, 60, 51, 100), (61, 90, 101, 200), 
               (91, 120, 201, 300), (121, 250, 301, 400), (251, 1000, 401, 500)]
               
    bp_pm10 = [(0, 50, 0, 50), (51, 100, 51, 100), (101, 250, 101, 200), 
               (251, 350, 201, 300), (351, 430, 301, 400), (431, 2000, 401, 500)]
               
    bp_no2 = [(0, 40, 0, 50), (41, 80, 51, 100), (81, 180, 101, 200), 
              (181, 280, 201, 300), (281, 400, 301, 400), (401, 2000, 401, 500)]
              
    bp_so2 = [(0, 40, 0, 50), (41, 80, 51, 100), (81, 380, 101, 200), 
              (381, 800, 201, 300), (801, 1600, 301, 400), (1601, 4000, 401, 500)]
              
    bp_co = [(0, 1.0, 0, 50), (1.1, 2.0, 51, 100), (2.1, 10.0, 101, 200), 
             (10.1, 17.0, 201, 300), (17.1, 34.0, 301, 400), (34.1, 100.0, 401, 500)]

    indices = {}
    if pm25 is not None: indices['PM2.5'] = get_sub_index(pm25, bp_pm25)
    if pm10 is not None: indices['PM10'] = get_sub_index(pm10, bp_pm10)
    if no2 is not None: indices['NO2'] = get_sub_index(no2, bp_no2)
    if so2 is not None: indices['SO2'] = get_sub_index(so2, bp_so2)
    if co is not None: indices['CO'] = get_sub_index(co, bp_co)

    if not indices:
        return 0, 'Unknown'
        
    dominant_pollutant = max(indices, key=indices.get)
    overall_aqi = indices[dominant_pollutant]
    
    return overall_aqi, dominant_pollutant
