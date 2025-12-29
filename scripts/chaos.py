#!/usr/bin/env python3
"""
Helper script to update chaos injection environment variables in docker-compose.yml
"""
import sys
import os

def update_chaos_var(service, var_name, value):
    """Update a chaos environment variable for a service in docker-compose.yml"""
    filename = 'docker-compose.yml'
    
    if not os.path.exists(filename):
        print(f"Error: {filename} not found. Run from project root.")
        return False
    
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    # Find the service section
    in_service = False
    in_environment = False
    updated = False
    service_indent = None
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            continue
        
        # Check if we're entering the target service section
        if stripped.startswith(service + ':'):
            in_service = True
            in_environment = False
            # Detect indentation level of service
            service_indent = len(line) - len(line.lstrip())
            continue
        
        # If we're in a service section, check if we've left it
        if in_service:
            current_indent = len(line) - len(line.lstrip())
            
            # If we hit a line with same or less indent than service, we've left
            if line and not line.isspace() and current_indent <= service_indent and ':' in line:
                if not stripped.startswith('#'):
                    break
            
            # Track when we enter the environment section (must be indented under service)
            if 'environment:' in line and current_indent > service_indent:
                in_environment = True
                continue
            
            # In the environment section, look for our variable
            if in_environment:
                if f'{var_name}=' in line:
                    # Replace the value (everything after the =)
                    parts = line.split('=')
                    if len(parts) >= 2:
                        # Preserve original spacing before the =
                        lines[i] = f'{parts[0]}={value}\n'
                        updated = True
                        break
                # If we hit another top-level key in environment section, check indentation
                if line.strip() and current_indent <= service_indent + 2:
                    # We've left the environment section
                    in_environment = False
    
    if not updated:
        print(f"Warning: Could not find {var_name} for service {service}")
        return False
    
    with open(filename, 'w') as f:
        f.writelines(lines)
    
    return True

def main():
    if len(sys.argv) != 4:
        print("Usage: chaos.py <service> <var_name> <value>")
        print("Example: chaos.py catalog CHAOS_LATENCY_MS 500")
        sys.exit(1)
    
    service = sys.argv[1]
    var_name = sys.argv[2]
    value = sys.argv[3]
    
    if update_chaos_var(service, var_name, value):
        print(f"Updated {var_name}={value} for {service}")
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()

