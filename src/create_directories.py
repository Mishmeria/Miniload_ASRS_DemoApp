import os

# Create directory structure
if not os.path.exists('views'):
    os.makedirs('views')

# Create an empty __init__.py file in the views directory
with open('views/__init__.py', 'w') as f:
    f.write('# Views package\n')