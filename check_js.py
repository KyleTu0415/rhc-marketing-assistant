import re

with open('frontend/sales.html', 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'<script>\n(.*?)\n</script>', content, re.DOTALL)
if not match:
    print('No script found')
    exit(1)

js = match.group(1)
lines = js.split('\n')

# Try to find the error by adding lines one by one
partial = ''
for i, line in enumerate(lines):
    partial += line + '\n'
    try:
        # Use Python to check for basic syntax issues
        # Actually, let's just find where RHC_INSIGHT_DATA ends
        if 'RHC_INSIGHT_DATA' in line and '];' in line:
            print(f'Line {i+1}: RHC_INSIGHT_DATA defined on single line, length={len(line)}')
            # Check if the line has proper ending
            if line.rstrip().endswith('];'):
                print('  Ends correctly with ];')
            else:
                print(f'  Does NOT end with ]; - ends with: {line.rstrip()[-20:]!r}')
    except Exception as e:
        print(f'Error at line {i+1}: {e}')
        print(f'  Line: {line[:100]}')
        break

# Also check for any obvious issues in the first 25 lines
print('\nFirst 25 lines summary:')
for i, line in enumerate(lines[:25]):
    status = 'OK'
    if 'var ' in line and not line.strip().startswith('//') and not line.strip().startswith('/*'):
        # Check if previous line ended properly
        if i > 0 and lines[i-1].strip() and not lines[i-1].rstrip().endswith(';') and not lines[i-1].rstrip().endswith('}') and not lines[i-1].rstrip().endswith(']'):
            if not lines[i-1].rstrip().endswith(','):
                status = 'WARN: prev line may not end properly'
    print(f'  {i+1}: {line[:80]}... {status}')
