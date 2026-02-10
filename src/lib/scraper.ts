import { Category } from '../types';

const CORS_PROXIES = [
    { url: 'https://api.allorigins.win/get?url=', parseJson: true, field: 'contents' },
    { url: 'https://api.codetabs.com/v1/proxy?quest=', parseJson: false, field: null },
    { url: 'https://corsproxy.io/?', parseJson: false, field: null },
];

export interface ClientScrapedLead {
    company_name: string;
    contact_name: string | null;
    email: string | null;
    phone: string | null;
    website: string | null;
    description: string | null;
    source_url: string;
    category_suggestion: string | null;
}

export interface ClientScrapeResult {
    leads: ClientScrapedLead[];
    error?: string;
}

async function fetchViaProxy(url: string): Promise<string> {
    let lastError: Error | null = null;

    for (const proxy of CORS_PROXIES) {
        try {
            const proxyUrl = proxy.url + encodeURIComponent(url);
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 12000);

            const response = await fetch(proxyUrl, {
                signal: controller.signal,
                headers: { 'Accept': 'text/html,application/json,*/*' },
            });
            clearTimeout(timeout);

            if (!response.ok) continue;

            let html = '';
            if (proxy.parseJson) {
                const data = await response.json();
                html = data[proxy.field!] || '';
            } else {
                html = await response.text();
            }

            if (html && html.length > 200) return html;
        } catch (err) {
            lastError = err as Error;
            continue;
        }
    }

    throw new Error(
        lastError?.message || 'All CORS proxies failed. Try using the Python backend for better results.'
    );
}

function extractEmails(html: string): string[] {
    const emailRegex = /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g;
    const emails = html.match(emailRegex) || [];
    const ignore = ['example.com', 'sentry.io', 'wixpress.com', 'w3.org', 'schema.org', 'google.com'];
    const ignoreExt = ['.png', '.jpg', '.gif', '.svg', '.css', '.js', '.woff', '.ttf', '.ico', '.webp'];

    return [...new Set(emails)]
        .filter(e => !ignore.some(i => e.toLowerCase().includes(i)))
        .filter(e => !ignoreExt.some(ext => e.toLowerCase().endsWith(ext)))
        .filter(e => !e.toLowerCase().startsWith('noreply'))
        .slice(0, 15);
}

function extractPhones(text: string): string[] {
    const phoneRegex = /(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}/g;
    const intlRegex = /\+?\d{1,3}[-.\s]?\d{4,5}[-.\s]?\d{4,6}/g;
    const phones = [...(text.match(phoneRegex) || []), ...(text.match(intlRegex) || [])];
    return [...new Set(phones)]
        .filter(p => p.replace(/\D/g, '').length >= 7 && p.replace(/\D/g, '').length <= 15)
        .slice(0, 10);
}

function extractCompanyName(html: string, url: string): string {
    // Try OG title
    const ogMatch = html.match(/<meta[^>]*property=["']og:title["'][^>]*content=["']([^"']+)["']/i);
    if (ogMatch) {
        const name = ogMatch[1].trim().split(/[|\-–—]/)[0].trim();
        if (name.length > 2 && name.length < 100) return name;
    }

    // Try <title>
    const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
    if (titleMatch) {
        const name = titleMatch[1].trim().split(/[|\-–—]/)[0].trim();
        if (name.length > 2 && name.length < 100) return name;
    }

    // Try H1
    const h1Match = html.match(/<h1[^>]*>([^<]+)<\/h1>/i);
    if (h1Match) {
        const name = h1Match[1].trim();
        if (name.length > 2 && name.length < 80) return name;
    }

    // Fallback: domain name
    try {
        const parsed = new URL(url);
        const domain = parsed.hostname.replace('www.', '').split('.')[0];
        return domain.charAt(0).toUpperCase() + domain.slice(1);
    } catch {
        return 'Unknown';
    }
}

function extractDescription(html: string): string {
    const ogDesc = html.match(/<meta[^>]*property=["']og:description["'][^>]*content=["']([^"']+)["']/i);
    if (ogDesc) return ogDesc[1].trim().substring(0, 300);

    const metaDesc = html.match(/<meta[^>]*name=["']description["'][^>]*content=["']([^"']+)["']/i);
    if (metaDesc) return metaDesc[1].trim().substring(0, 300);

    // Fallback: grab first meaningful <p>
    const pMatch = html.match(/<p[^>]*>(.{50,300}?)<\/p>/i);
    if (pMatch) return pMatch[1].replace(/<[^>]+>/g, '').trim().substring(0, 300);

    return '';
}

function extractContactName(html: string): string | null {
    // JSON-LD Person
    const ldMatch = html.match(/"@type"\s*:\s*"Person"[^}]*"name"\s*:\s*"([^"]+)"/i);
    if (ldMatch) return ldMatch[1];

    // Meta author
    const authorMatch = html.match(/<meta[^>]*name=["']author["'][^>]*content=["']([^"']+)["']/i);
    if (authorMatch) return authorMatch[1].trim();

    return null;
}

const CATEGORY_KEYWORDS: Record<string, string[]> = {
    Technology: ['software', 'tech', 'digital', 'cloud', 'api', 'saas', 'developer', 'ai', 'data', 'platform'],
    Healthcare: ['health', 'medical', 'hospital', 'clinic', 'doctor', 'pharma', 'wellness', 'dental'],
    Finance: ['finance', 'bank', 'invest', 'insurance', 'fintech', 'trading', 'loan', 'credit'],
    'E-commerce': ['shop', 'store', 'ecommerce', 'retail', 'product', 'cart', 'marketplace', 'buy'],
    Marketing: ['marketing', 'agency', 'advertis', 'brand', 'seo', 'social media', 'campaign'],
    Education: ['education', 'school', 'university', 'learning', 'course', 'training', 'student'],
    'Real Estate': ['real estate', 'property', 'home', 'apartment', 'rent', 'mortgage', 'realty'],
    Legal: ['law', 'legal', 'attorney', 'lawyer', 'litigation', 'counsel'],
    Manufacturing: ['manufactur', 'industrial', 'factory', 'production', 'supply chain'],
};

function categorizeFromText(text: string): string | null {
    const lower = text.toLowerCase();
    let best: string | null = null;
    let maxScore = 0;
    for (const [cat, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
        const score = keywords.filter(kw => lower.includes(kw)).length;
        if (score > maxScore) { maxScore = score; best = cat; }
    }
    return best;
}

export async function scrapeWebsite(url: string, _categories?: Category[]): Promise<ClientScrapeResult> {
    try {
        const html = await fetchViaProxy(url);

        const emails = extractEmails(html);
        const phones = extractPhones(html);
        const companyName = extractCompanyName(html, url);
        const description = extractDescription(html);
        const contactName = extractContactName(html);
        const category = categorizeFromText(html);

        const leads: ClientScrapedLead[] = [];

        if (emails.length > 0) {
            for (let i = 0; i < emails.length; i++) {
                leads.push({
                    company_name: companyName,
                    contact_name: i === 0 ? contactName : null,
                    email: emails[i],
                    phone: phones[i] || phones[0] || null,
                    website: url,
                    description: i === 0 ? description : null,
                    source_url: url,
                    category_suggestion: category,
                });
            }
        } else if (phones.length > 0) {
            for (let i = 0; i < phones.length; i++) {
                leads.push({
                    company_name: companyName,
                    contact_name: i === 0 ? contactName : null,
                    email: null,
                    phone: phones[i],
                    website: url,
                    description: i === 0 ? description : null,
                    source_url: url,
                    category_suggestion: category,
                });
            }
        } else {
            leads.push({
                company_name: companyName,
                contact_name: contactName,
                email: null,
                phone: null,
                website: url,
                description: description,
                source_url: url,
                category_suggestion: category,
            });
        }

        return { leads };
    } catch (err: any) {
        return { leads: [], error: err.message || 'Scraping failed' };
    }
}
