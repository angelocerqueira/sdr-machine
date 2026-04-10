"""Tech stack detection patterns.

Minimal set of patterns inspired by the Wappalyzer open-source dataset.
Format: list of (pattern_regex, name, category, source).
`source` is one of: "html", "header_value", "header_name".
"""

HTML_PATTERNS = [
    (r"wp-content/|wp-includes/|/wp-json/", "WordPress", "cms"),
    (r"cdn\.shopify\.com|shopify\.com/s/", "Shopify", "ecommerce"),
    (r"wix\.com|static\.wixstatic\.com", "Wix", "website_builder"),
    (r"squarespace\.com|static1\.squarespace\.com", "Squarespace", "website_builder"),
    (r"webnode\.com|site123\.com", "Webnode/Site123", "website_builder"),
    (r"static\.parastorage\.com", "Wix", "website_builder"),
    (r"googletagmanager\.com/gtag|gtag\.js", "Google Analytics", "analytics"),
    (r"googletagmanager\.com/gtm", "Google Tag Manager", "analytics"),
    (r"connect\.facebook\.net/.*fbevents\.js|fbq\(", "Facebook Pixel", "analytics"),
    (r"hotjar\.com/c/hotjar", "Hotjar", "analytics"),
    (r"tidio\.co|code\.tidio\.co", "Tidio", "chat"),
    (r"crisp\.chat", "Crisp", "chat"),
    (r"intercom\.io|widget\.intercom\.io", "Intercom", "chat"),
    (r"tawk\.to|embed\.tawk\.to", "Tawk.to", "chat"),
    (r"_next/static|__NEXT_DATA__", "Next.js", "framework"),
    (r"react\.production|react-dom", "React", "framework"),
    (r"vue\.min\.js|__vue__", "Vue.js", "framework"),
    (r"type=\"application/x-shockwave-flash\"|Adobe Flash", "Adobe Flash", "runtime"),
    (r"jquery-1\.|jquery\.min\.js\?v=1", "jQuery 1", "js_library"),
]

META_GENERATOR_PATTERNS = [
    (r"wix\.com", "Wix", "website_builder"),
    (r"wordpress", "WordPress", "cms"),
    (r"drupal", "Drupal", "cms"),
    (r"joomla", "Joomla", "cms"),
    (r"shopify", "Shopify", "ecommerce"),
    (r"squarespace", "Squarespace", "website_builder"),
]

HEADER_PATTERNS = [
    ("x-powered-by", r"php", "PHP", "language"),
    ("x-powered-by", r"asp\.net", "ASP.NET", "framework"),
    ("x-powered-by", r"express", "Express.js", "framework"),
    ("server", r"nginx", "Nginx", "web_server"),
    ("server", r"apache", "Apache", "web_server"),
    ("server", r"cloudflare", "Cloudflare", "cdn"),
]
