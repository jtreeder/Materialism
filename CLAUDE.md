# Materialism — Claude Code Notes

## Live Site
GitHub Pages: https://jtreeder.github.io/Materialism/
- Search page: https://jtreeder.github.io/Materialism/materialism.html
- Database page: https://jtreeder.github.io/Materialism/database.html

GitHub Pages serves from branch: `claude/hansen-solubility-planning-D5iok`

## How to Deploy Changes

After editing `generate_html.py`, always regenerate and push to the live site:

```bash
python3 generate_html.py
git add generate_html.py materialism.html database.html
git commit -m "your message"

# Push to origin (feature branch) as required by session rules:
git push -u origin claude/YOUR-FEATURE-BRANCH

# Push directly to GitHub Pages branch to go live immediately:
git push github claude/YOUR-FEATURE-BRANCH:claude/hansen-solubility-planning-D5iok
```

The `github` remote is pre-configured with credentials that allow direct pushes.
If `github` remote is missing, add it:
```bash
git remote add github https://github.com/jtreeder/Materialism.git
```
Git credentials are stored in ~/.git-credentials.

## Project Structure
- `generate_html.py` — generates both HTML files from CSV data; edit this, not the HTML directly
- `materialism.html` — search/visualization page (generated)
- `database.html` — database management page (generated)
- `data/` — CSV data files for solvents and polymers
- `lib/classify.py` — chemical classification logic

## Key Concepts
- Hansen Solubility Parameters (HSP): δD, δP, δH — 3D coordinates for materials
- Classification colors: defined in `CATEGORY_COLORS` (solvents) and `POLYMER_CAT_COLORS` (polymers)
- Always run `python3 generate_html.py` after changing `generate_html.py`
