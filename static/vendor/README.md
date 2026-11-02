# Locally served UI dependencies

The dashboard loads these assets from Flask's `static/` directory. No runtime CDN or Google Fonts request is required.

| Asset | Version | Source | License |
| --- | --- | --- | --- |
| Bootstrap CSS | 5.3.8 | https://getbootstrap.com/docs/5.3/getting-started/introduction/ | MIT; see `bootstrap/LICENSE` |
| Bootstrap Icons CSS and web font | 1.13.1 | https://github.com/twbs/icons/tree/v1.13.1 | MIT; see `bootstrap-icons/LICENSE` |
| Manrope variable font | Google Fonts distribution, retrieved 2 November 2026 | https://github.com/google/fonts/tree/main/ofl/manrope | SIL Open Font License 1.1; see `../fonts/manrope/OFL.txt` |

Bootstrap is used for buttons, form controls, navigation, badges and accessibility helpers. Existing application JavaScript handles charts, data refresh and navigation; Bootstrap's JavaScript bundle is not needed for these controls. Custom project styles load after the vendor styles.

Bootstrap CSS SHA-384 (verified against the official documentation): `sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB`.
