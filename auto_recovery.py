import os
import datetime
from city_routing import CITY_ROUTING, WORKING_CITIES

class AutoRecovery:
    def __init__(self):
        self.routing_config = CITY_ROUTING
        self.working_cities = WORKING_CITIES
        self.recovery_log = []

    def execute_routing(self, city):
        """Check if a city needs routing to a working alternative"""
        if city in self.routing_config:
            routing_target = self.routing_config[city]['route_to']
            reason = self.routing_config[city]['reason']
            print(f"🔄 Auto-routing {city} -> {routing_target} ({reason})")
            self.log_recovery_action(city, "ROUTING_EXECUTED", f"{city} -> {routing_target}")
            return routing_target
        return None

    def check_city_health(self, city):
        """Check if a city API is healthy (placeholder for future implementation)"""
        # This would implement actual API health checking
        # For now, just check if city is in routing config
        return city not in self.routing_config

    def get_system_status(self):
        """Return overall system status"""
        routed_cities = list(self.routing_config.keys())
        total_cities = len(self.working_cities) + len(routed_cities)

        return {
            'total_cities': total_cities,
            'working_cities': len(self.working_cities),
            'routed_cities': len(routed_cities),
            'routing_config': self.routing_config,
            'last_recovery_actions': self.recovery_log[-5:] if self.recovery_log else []
        }

    def log_recovery_action(self, city, action_type, details):
        """Log recovery actions for monitoring"""
        timestamp = datetime.datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'city': city,
            'action': action_type,
            'details': details
        }
        self.recovery_log.append(log_entry)

        # Also write to file for persistence
        log_file = 'logs/recovery.log'
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'a') as f:
            f.write(f"{timestamp} | {city} | {action_type} | {details}\n")

# Global instance
auto_recovery = AutoRecovery()